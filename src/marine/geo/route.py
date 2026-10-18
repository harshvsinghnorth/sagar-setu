"""Route search: A* over a sea grid, cost from waves, wind and current against the heading.

The route never decides whether it is safe to go (CLAUDE.md rule 1). It finds the cheapest
path that stays inside India's EEZ, clear of the IMBL by a margin, off land, and out of
cells already at a do-not-sail level; the risk engine then judges the conditions the route
actually passes through. Pure functions on arrays plus the static boundary data — no
network, no model — so every rule here is unit-tested.

Grid cells are ~2 km. Forecast values come from coarser model nodes (Open-Meteo, ~0.1°):
each cell takes the values of its nearest node.
"""

from __future__ import annotations

import heapq
import math
import time
from dataclasses import dataclass, field

import numpy as np
import shapely
from shapely.geometry import MultiLineString

from marine.geo.boundaries import load_eez, load_imbl, load_india_union
from marine.geo.geodesy import LocalPlane, haversine_km, initial_bearing_deg
from marine.risk.thresholds import TABLES, VesselClass

KMH_PER_KT = 1.852
# 8-connected moves: (d_row, d_col)
MOVES = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]


@dataclass(frozen=True)
class SeaField:
    """Forecast values at model nodes — worst of each over the departure window.

    Directions follow the source conventions: waves and wind are the direction they come
    FROM; current is the direction it flows TOWARDS.
    """

    lats: np.ndarray
    lons: np.ndarray
    wave_m: np.ndarray
    period_s: np.ndarray
    wave_from_deg: np.ndarray
    wind_kt: np.ndarray
    wind_from_deg: np.ndarray
    current_kt: np.ndarray
    current_to_deg: np.ndarray

    def __len__(self) -> int:
        return len(self.lats)


@dataclass(frozen=True)
class Grid:
    lats: np.ndarray  # (ny,) cell-centre latitudes, south → north
    lons: np.ndarray  # (nx,) cell-centre longitudes, west → east
    navigable: np.ndarray  # (ny, nx) inside India's EEZ and ≥ margin from every IMBL
    in_eez: np.ndarray  # (ny, nx) inside India's EEZ at all
    foreign: np.ndarray  # (ny, nx) not Indian sea or land: another state's water or land
    imbl_km: np.ndarray  # (ny, nx) distance to the nearest IMBL
    node: np.ndarray  # (ny, nx) index of the nearest SeaField node
    margin_km: float

    @property
    def shape(self) -> tuple[int, int]:
        return self.navigable.shape


@dataclass(frozen=True)
class LineCheck:
    """What sailing the straight line would mean."""

    distance_km: float
    crosses_border: bool
    crosses_land: bool
    min_imbl_km: float
    max_wave_m: float | None
    max_wind_kt: float | None


@dataclass(frozen=True)
class RouteResult:
    found: bool
    reason: str | None
    path: list[tuple[float, float]] = field(default_factory=list)  # (lat, lon), smoothed
    distance_km: float = 0.0
    eta_min: float = 0.0
    max_wave_m: float | None = None
    max_period_at_max_wave_s: float | None = None
    max_wind_kt: float | None = None
    max_steepness: float | None = None
    min_imbl_km: float | None = None
    start_snap_km: float = 0.0
    end_snap_km: float = 0.0
    nodes: list[int] = field(default_factory=list)  # SeaField nodes the route passes
    avoided_hazard: bool = False  # had to detour round do-not-sail water
    direct: LineCheck | None = None
    cells: int = 0
    compute_ms: float = 0.0


# -- grid ------------------------------------------------------------------------------------


def nearest_nodes(lats: np.ndarray, lons: np.ndarray, sea: SeaField) -> np.ndarray:
    """Index of the nearest SeaField node for every (lat, lon) pair (flat arrays)."""
    cos0 = math.cos(math.radians(float(np.mean(lats))))
    dy = lats[:, None] - sea.lats[None, :]
    dx = (lons[:, None] - sea.lons[None, :]) * cos0
    return np.argmin(dx * dx + dy * dy, axis=1)


def build_grid(
    south: float,
    west: float,
    north: float,
    east: float,
    sea: SeaField,
    *,
    step_deg: float = 0.02,
    margin_km: float = 2.0,
) -> Grid:
    lats = np.arange(south, north + step_deg / 2, step_deg)
    lons = np.arange(west, east + step_deg / 2, step_deg)
    lon2, lat2 = np.meshgrid(lons, lats)
    in_eez, foreign = _classify(lon2, lat2)

    plane = LocalPlane(float(np.mean(lats)), float(np.mean(lons)))
    lines = [plane.to_xy_array(b.coords) for b in load_imbl()]
    xy = plane.to_xy_array(np.column_stack([lon2.ravel(), lat2.ravel()]))
    pts = shapely.points(xy[:, 0], xy[:, 1])
    imbl_km = shapely.distance(pts, MultiLineString(lines)).reshape(lat2.shape)

    node = nearest_nodes(lat2.ravel(), lon2.ravel(), sea).reshape(lat2.shape)
    navigable = in_eez & (imbl_km >= margin_km)
    return Grid(lats, lons, navigable, in_eez, foreign, imbl_km, node, margin_km)


def _classify(lons: np.ndarray, lats: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(inside India's EEZ, foreign). Indian land is neither: inside the EEZ+land union but
    outside the EEZ — so land near the IMBL (Rameswaram island) is not mistaken for the
    other state's water."""
    eez, union = load_eez(), load_india_union()
    shapely.prepare(eez)
    shapely.prepare(union)
    return shapely.contains_xy(eez, lons, lats), ~shapely.contains_xy(union, lons, lats)


def _cell_of(grid: Grid, lat: float, lon: float) -> tuple[int, int]:
    i = int(np.clip(np.argmin(np.abs(grid.lats - lat)), 0, len(grid.lats) - 1))
    j = int(np.clip(np.argmin(np.abs(grid.lons - lon)), 0, len(grid.lons) - 1))
    return i, j


def _snap(grid: Grid, cell: tuple[int, int], passable: np.ndarray, max_km: float):
    """Nearest passable cell to `cell` within max_km, or None."""
    if passable[cell]:
        return cell, 0.0
    ys, xs = np.nonzero(passable)
    if len(ys) == 0:
        return None
    lat0, lon0 = grid.lats[cell[0]], grid.lons[cell[1]]
    d = np.array(
        [haversine_km(lat0, lon0, grid.lats[y], grid.lons[x]) for y, x in zip(ys, xs, strict=True)]
    )
    k = int(np.argmin(d))
    return ((int(ys[k]), int(xs[k])), float(d[k])) if d[k] <= max_km else None


# -- cost ------------------------------------------------------------------------------------


def _headness(travel_deg: float, from_deg: float) -> float:
    """1 when heading straight into it, 0 when it is directly astern."""
    return 0.5 * (1.0 + math.cos(math.radians(travel_deg - from_deg)))


def travel_hours(dist_km: float, bearing: float, sea: SeaField, n: int, speed_kt: float) -> float:
    """Plain travel time at speed made good: the current along the heading helps or hinders."""
    along = sea.current_kt[n] * math.cos(math.radians(bearing - sea.current_to_deg[n]))
    return dist_km / (max(speed_kt + along, 0.3 * speed_kt) * KMH_PER_KT)


def sea_penalty(bearing: float, sea: SeaField, n: int, vessel: VesselClass) -> float:
    """≥ 1. Grows with wave height, wind and steepness relative to the vessel's caution
    thresholds, and more when the sea or wind is on the bow than astern."""
    th = TABLES[vessel]
    hs, wind = sea.wave_m[n], sea.wind_kt[n]
    steep = hs / sea.period_s[n] ** 2 if sea.period_s[n] > 0 else 0.0
    p_wave = 1 + 0.6 * (hs / th.wave_height_m.caution) ** 2 * (
        0.5 + _headness(bearing, sea.wave_from_deg[n])
    )
    p_wind = 1 + 0.3 * (wind / th.wind_kt.caution) ** 2 * (
        0.5 + _headness(bearing, sea.wind_from_deg[n])
    )
    p_steep = 1 + 0.5 * (steep / th.steepness.caution) ** 2
    return p_wave * p_wind * p_steep


def step_hours(
    dist_km: float, bearing: float, sea: SeaField, n: int, vessel: VesselClass, speed_kt: float
) -> float:
    """Search cost of one step: travel time inflated by the sea state."""
    return travel_hours(dist_km, bearing, sea, n, speed_kt) * sea_penalty(bearing, sea, n, vessel)


def hazard_mask(grid: Grid, sea: SeaField, vessel: VesselClass) -> np.ndarray:
    """Cells already at a do-not-sail level for this vessel on any routed parameter."""
    th = TABLES[vessel]
    n = grid.node
    steep = np.where(sea.period_s > 0, sea.wave_m / np.maximum(sea.period_s, 1e-6) ** 2, 0.0)
    return (
        (sea.wave_m[n] >= th.wave_height_m.no_go)
        | (sea.wind_kt[n] >= th.wind_kt.no_go)
        | (steep[n] >= th.steepness.no_go)
    )


# -- search ----------------------------------------------------------------------------------


def astar(
    grid: Grid,
    sea: SeaField,
    passable: np.ndarray,
    start: tuple[int, int],
    goal: tuple[int, int],
    vessel: VesselClass,
    speed_kt: float,
) -> list[tuple[int, int]] | None:
    ny, nx = passable.shape
    k_lat = 111.195
    cos0 = math.cos(math.radians(float(np.mean(grid.lats))))
    dlat = float(grid.lats[1] - grid.lats[0]) if ny > 1 else 0.02
    dlon = float(grid.lons[1] - grid.lons[0]) if nx > 1 else 0.02
    v_max_kmh = (speed_kt + float(np.max(sea.current_kt, initial=0.0))) * KMH_PER_KT
    g_lat, g_lon = grid.lats[goal[0]], grid.lons[goal[1]]

    def h(c: tuple[int, int]) -> float:  # admissible: penalties are all ≥ 1
        return haversine_km(grid.lats[c[0]], grid.lons[c[1]], g_lat, g_lon) / v_max_kmh

    best = {start: 0.0}
    came: dict[tuple[int, int], tuple[int, int]] = {}
    heap = [(h(start), 0.0, start)]
    while heap:
        _, g, cur = heapq.heappop(heap)
        if cur == goal:
            path = [cur]
            while cur in came:
                cur = came[cur]
                path.append(cur)
            return path[::-1]
        if g > best.get(cur, math.inf):
            continue
        for di, dj in MOVES:
            nb = (cur[0] + di, cur[1] + dj)
            if not (0 <= nb[0] < ny and 0 <= nb[1] < nx) or not passable[nb]:
                continue
            dy_km, dx_km = di * dlat * k_lat, dj * dlon * k_lat * cos0
            dist = math.hypot(dx_km, dy_km)
            bearing = (math.degrees(math.atan2(dx_km, dy_km)) + 360.0) % 360.0
            ng = g + step_hours(dist, bearing, sea, int(grid.node[nb]), vessel, speed_kt)
            if ng < best.get(nb, math.inf):
                best[nb] = ng
                came[nb] = cur
                heapq.heappush(heap, (ng + h(nb), ng, nb))
    return None


def _segment_ok(grid: Grid, passable: np.ndarray, a: tuple[int, int], b: tuple[int, int]) -> bool:
    """Every cell under the straight segment a→b is passable (sampled at ½-cell spacing)."""
    steps = max(abs(b[0] - a[0]), abs(b[1] - a[1])) * 2 + 1
    for t in np.linspace(0.0, 1.0, steps):
        c = (round(a[0] + (b[0] - a[0]) * t), round(a[1] + (b[1] - a[1]) * t))
        if not passable[c]:
            return False
    return True


def smooth(grid: Grid, passable: np.ndarray, cells: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """String-pulling: skip waypoints while the straight shortcut stays legal water."""
    if len(cells) <= 2:
        return cells
    out = [cells[0]]
    i = 0
    while i < len(cells) - 1:
        j = len(cells) - 1
        while j > i + 1 and not _segment_ok(grid, passable, cells[i], cells[j]):
            j -= 1
        out.append(cells[j])
        i = j
    return out


def check_line(
    grid: Grid, sea: SeaField, a: tuple[float, float], b: tuple[float, float]
) -> LineCheck:
    """Sample the straight line a→b (lat, lon) every ~0.5 km."""
    dist = haversine_km(*a, *b)
    n = max(int(dist / 0.5), 2)
    lats = np.linspace(a[0], b[0], n)
    lons = np.linspace(a[1], b[1], n)
    in_eez, foreign = _classify(lons, lats)
    land = ~in_eez & ~foreign
    cells = [_cell_of(grid, la, lo) for la, lo in zip(lats, lons, strict=True)]
    imbl = [float(grid.imbl_km[c]) for c in cells]
    nodes = nearest_nodes(lats, lons, sea)
    # A harbour sits on land: skip the land the line starts and ends on; any land left in
    # between is a real crossing (an island or a headland in the way).
    i, j = 0, len(land)
    while i < j and land[i]:
        i += 1
    while j > i and land[j - 1]:
        j -= 1
    return LineCheck(
        round(dist, 1),
        bool(np.any(foreign)),
        bool(np.any(land[i:j])),
        round(min(imbl), 1),
        round(float(np.max(sea.wave_m[nodes])), 2) if len(sea) else None,
        round(float(np.max(sea.wind_kt[nodes])), 1) if len(sea) else None,
    )


def plan_route(
    start: tuple[float, float],
    goal: tuple[float, float],
    sea: SeaField,
    *,
    vessel: VesselClass = VesselClass.TRADITIONAL,
    speed_kt: float = 7.0,
    margin_km: float = 2.0,
    step_deg: float = 0.02,
    snap_km: float = 12.0,
) -> RouteResult:
    """Cheapest legal sea route from start to goal (both (lat, lon)).

    Hard constraints: inside India's EEZ, ≥ margin_km from every IMBL, off land. Soft:
    do-not-sail cells are avoided if any route avoids them; otherwise the route goes through
    and the risk engine's verdict will say so.
    """
    t0 = time.perf_counter()
    span = max(abs(goal[0] - start[0]), abs(goal[1] - start[1]))
    pad = max(0.15, 0.3 * span)
    grid = build_grid(
        min(start[0], goal[0]) - pad,
        min(start[1], goal[1]) - pad,
        max(start[0], goal[0]) + pad,
        max(start[1], goal[1]) + pad,
        sea,
        step_deg=step_deg,
        margin_km=margin_km,
    )
    direct = check_line(grid, sea, start, goal)
    gi = _cell_of(grid, *goal)
    if grid.foreign[gi]:
        return RouteResult(
            False,
            "the destination is outside Indian waters, across the maritime boundary",
            direct=direct,
            cells=grid.navigable.size,
            compute_ms=round((time.perf_counter() - t0) * 1000, 1),
        )

    hazard = hazard_mask(grid, sea, vessel)
    attempts = [(grid.navigable & ~hazard, False), (grid.navigable, True)]
    for passable, through_hazard in attempts:
        s = _snap(grid, _cell_of(grid, *start), passable, snap_km)
        g = _snap(grid, gi, passable, snap_km)
        if s is None or g is None:
            continue
        cells = astar(grid, sea, passable, s[0], g[0], vessel, speed_kt)
        if cells is None:
            continue
        wp = smooth(grid, passable, cells)
        path = [(round(float(grid.lats[i]), 4), round(float(grid.lons[j]), 4)) for i, j in wp]
        dist = sum(haversine_km(*path[k], *path[k + 1]) for k in range(len(path) - 1))
        hours = sum(
            travel_hours(
                haversine_km(*path[k], *path[k + 1]),
                initial_bearing_deg(*path[k], *path[k + 1]),
                sea,
                int(grid.node[wp[k + 1]]),
                speed_kt,
            )
            for k in range(len(path) - 1)
        )
        used = sorted({int(grid.node[c]) for c in cells})
        i_wave = max(used, key=lambda n: sea.wave_m[n])
        steep = [sea.wave_m[n] / sea.period_s[n] ** 2 for n in used if sea.period_s[n] > 0]
        return RouteResult(
            True,
            None if not through_hazard else "no route avoids do-not-sail water",
            path,
            round(dist, 1),
            round(hours * 60),
            round(float(sea.wave_m[i_wave]), 2),
            round(float(sea.period_s[i_wave]), 1),
            round(float(max(sea.wind_kt[n] for n in used)), 1),
            round(float(max(steep)), 4) if steep else None,
            round(float(min(grid.imbl_km[c] for c in cells)), 1),
            round(s[1], 1),
            round(g[1], 1),
            used,
            avoided_hazard=bool(hazard.any()) and not through_hazard,
            direct=direct,
            cells=grid.navigable.size,
            compute_ms=round((time.perf_counter() - t0) * 1000, 1),
        )
    return RouteResult(
        False,
        "no legal sea route found inside Indian waters",
        direct=direct,
        cells=grid.navigable.size,
        compute_ms=round((time.perf_counter() - t0) * 1000, 1),
    )
