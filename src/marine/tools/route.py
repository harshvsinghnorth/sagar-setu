"""Route tool: fetch a forecast grid around the trip, search the route, record the evidence.

Open-Meteo answers a whole grid of points in one request (verified 2026-10-18: 81 points in
1.3–1.6 s). Each grid node is reduced to its worst over the departure window — the highest
wave with the period and direction at that hour, the strongest wind — the same worst-of rule
the risk engine applies at the harbour. Only the nodes the route actually passes are written
to the ledger (as `route_*` variables, so they never mix into the harbour's own summary), and
the risk engine then grades the worst of harbour and route together.

No grid (network down, nothing cached): the harbour's own forecast is applied to the whole
area — the route still respects the border and the land, and the answer says the sea state
along it was not resolved. Degrade loudly (CLAUDE.md rule 3).
"""

from __future__ import annotations

import asyncio
import math
from datetime import UTC, datetime

import numpy as np
from pydantic import BaseModel, Field

from marine.geo.geodesy import compass_point, haversine_km, initial_bearing_deg
from marine.geo.route import RouteResult, SeaField, plan_route, route_bbox
from marine.ledger import Observation
from marine.risk.thresholds import VesselClass
from marine.sources.base import CONFIDENCE, FetchOutcome, PointQuery, try_fallback, try_live
from marine.sources.open_meteo import KMH_TO_KT, OpenMeteoMarine, OpenMeteoWeather
from marine.tools.context import ToolContext

GRID_STEP = 0.1  # degrees — about the Open-Meteo marine model's own spacing
MAX_NODES = 300
GRID_TIMEOUT_S = 8.0  # a grid is a bigger request than a point; still well inside the budget


class RouteQuery(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    dest_lat: float = Field(ge=-90, le=90)
    dest_lon: float = Field(ge=-180, le=180)
    dest_label: str
    start: datetime
    end: datetime
    vessel: VesselClass = VesselClass.TRADITIONAL
    speed_kt: float = Field(default=7.0, gt=0, le=30)
    margin_km: float = Field(default=2.0, ge=0.5, le=20)


class RouteLeg(BaseModel):
    compass: str
    bearing_deg: float
    distance_km: float


class RouteSummary(BaseModel):
    destination: str
    dest_lat: float
    dest_lon: float
    found: bool
    reason: str | None = None
    path: list[tuple[float, float]] = Field(default_factory=list)  # (lat, lon)
    legs: list[RouteLeg] = Field(default_factory=list)
    distance_km: float = 0.0
    eta_min: float = 0.0
    speed_kt: float = 7.0
    margin_km: float = 2.0
    min_imbl_km: float | None = None
    max_wave_m: float | None = None
    period_at_max_wave_s: float | None = None
    max_wind_kt: float | None = None
    avoided_hazard: bool = False
    direct_distance_km: float = 0.0
    direct_bearing_deg: float = 0.0
    direct_compass: str = ""
    direct_crosses_border: bool = False
    direct_crosses_land: bool = False
    direct_min_imbl_km: float = 0.0
    sea_state_source: str = "grid"  # "grid" | "harbour_only"
    observation_ids: list[str] = Field(default_factory=list)
    compute_ms: float = 0.0


# -- grid fetch ------------------------------------------------------------------------------


def grid_nodes(south: float, west: float, north: float, east: float) -> list[tuple[float, float]]:
    step = GRID_STEP
    while True:
        lats = np.arange(math.floor(south / step) * step, north + step, step)
        lons = np.arange(math.floor(west / step) * step, east + step, step)
        if len(lats) * len(lons) <= MAX_NODES:
            return [(round(float(a), 3), round(float(o), 3)) for a in lats for o in lons]
        step *= 1.5


def _grid_url(base: str, nodes: list[tuple[float, float]], hourly: str, extra: str = "") -> str:
    lats = ",".join(f"{a:g}" for a, _ in nodes)
    lons = ",".join(f"{o:g}" for _, o in nodes)
    return (
        f"{base}?latitude={lats}&longitude={lons}&hourly={hourly}"
        f"&forecast_days=3&timezone=UTC{extra}"
    )


async def _fetch(url: str) -> FetchOutcome | None:
    out = await try_live(url, OpenMeteoMarine.ttl, GRID_TIMEOUT_S)
    if isinstance(out, str):  # no snapshot exists for an arbitrary grid: stale cache or nothing
        out = try_fallback(url, out, None, None, None)
    return out


def _window_index(times: list[str], start: datetime, end: datetime) -> list[int]:
    return [
        i
        for i, t in enumerate(times)
        if start <= datetime.fromisoformat(t).replace(tzinfo=UTC) <= end
    ]


def _worst_by_node(marine: list[dict], weather: list[dict], start: datetime, end: datetime):
    """Per node: (lat, lon, valid_time, wave, period, wave_from, wind, wind_from, cur_kt,
    cur_to) — the worst over the window, with the companions at the worst wave's hour."""
    rows = []
    for m, w in zip(marine, weather, strict=False):
        mh, wh = m.get("hourly") or {}, w.get("hourly") or {}
        idx = _window_index(mh.get("time", []), start, end)
        wave = [(mh["wave_height"][i], i) for i in idx if mh["wave_height"][i] is not None]
        widx = _window_index(wh.get("time", []), start, end)
        wind = [(wh["wind_speed_10m"][i], i) for i in widx if wh["wind_speed_10m"][i] is not None]
        if not wave or not wind:
            continue
        hs, i = max(wave)
        ws, j = max(wind)
        rows.append(
            (
                float(m["latitude"]),
                float(m["longitude"]),
                datetime.fromisoformat(mh["time"][i]).replace(tzinfo=UTC),
                float(hs),
                float(mh["wave_period"][i] or 0.0),
                float(mh["wave_direction"][i] or 0.0),
                float(ws),
                float(wh["wind_direction_10m"][j] or 0.0),
                float(mh["ocean_current_velocity"][i] or 0.0) * KMH_TO_KT,
                float(mh["ocean_current_direction"][i] or 0.0),
            )
        )
    return rows


async def _harbour_rows(q: RouteQuery):
    """Fallback sea state: the harbour's own forecast, from the normal point chain (which ends
    in the frozen snapshot), applied to every node."""
    pq = PointQuery(lat=q.lat, lon=q.lon, start=q.start, end=q.end)
    got = await asyncio.gather(
        OpenMeteoMarine().fetch(pq), OpenMeteoWeather().fetch(pq), return_exceptions=True
    )
    if any(isinstance(g, BaseException) for g in got):
        return [], None
    obs = got[0] + got[1]

    def worst(var: str) -> Observation | None:
        xs = [o for o in obs if o.variable == var]
        return max(xs, key=lambda o: o.value) if xs else None

    hs, wind = worst("significant_wave_height"), worst("wind_speed")
    if not hs or not wind:
        return [], None

    def at(var: str, t: datetime) -> float:
        xs = [o for o in obs if o.variable == var]
        return min(xs, key=lambda o: abs((o.valid_time - t).total_seconds())).value if xs else 0.0

    row = (
        q.lat,
        q.lon,
        hs.valid_time,
        hs.value,
        at("wave_period", hs.valid_time),
        at("wave_direction", hs.valid_time),
        wind.value,
        at("wind_direction", wind.valid_time),
        at("current_speed", hs.valid_time),
        at("current_direction", hs.valid_time),
    )
    return [row], hs


def _field(rows) -> SeaField:
    a = np.asarray([r[:2] + r[3:] for r in rows], dtype=float)  # drop the datetime column
    return SeaField(*(a[:, k] for k in range(a.shape[1])))


# -- the tool --------------------------------------------------------------------------------


def _legs(path: list[tuple[float, float]]) -> list[RouteLeg]:
    out = []
    for a, b in zip(path, path[1:], strict=False):
        brg = initial_bearing_deg(*a, *b)
        out.append(
            RouteLeg(
                compass=compass_point(brg),
                bearing_deg=round(brg),
                distance_km=round(haversine_km(*a, *b), 1),
            )
        )
    return out


def _dist_to_path(lat: float, lon: float, path: list[tuple[float, float]]) -> float:
    pts = []
    for a, b in zip(path, path[1:], strict=False):
        k = max(int(haversine_km(*a, *b)), 1)
        pts += [
            (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t) for t in np.linspace(0, 1, k + 1)
        ]
    return min(haversine_km(lat, lon, *p) for p in (pts or path))


async def plan_sea_route(ctx: ToolContext, q: RouteQuery) -> RouteSummary:
    start, goal = (q.lat, q.lon), (q.dest_lat, q.dest_lon)
    nodes = grid_nodes(*route_bbox(start, goal))
    m_out, w_out = await asyncio.gather(
        _fetch(
            _grid_url(
                "https://marine-api.open-meteo.com/v1/marine",
                nodes,
                "wave_height,wave_period,wave_direction,ocean_current_velocity,ocean_current_direction",
            )
        ),
        _fetch(
            _grid_url(
                "https://api.open-meteo.com/v1/forecast",
                nodes,
                "wind_speed_10m,wind_direction_10m",
                "&wind_speed_unit=kn",
            )
        ),
    )
    rows, sea_source, outcome, prov_obs = [], "grid", m_out, None
    if m_out and w_out:
        as_list = lambda p: p if isinstance(p, list) else [p]  # noqa: E731
        rows = _worst_by_node(as_list(m_out.payload), as_list(w_out.payload), q.start, q.end)
    if not rows:
        rows, prov_obs = await _harbour_rows(q)
        sea_source, outcome = "harbour_only", None
    summary = RouteSummary(
        destination=q.dest_label,
        dest_lat=q.dest_lat,
        dest_lon=q.dest_lon,
        found=False,
        speed_kt=q.speed_kt,
        margin_km=q.margin_km,
        sea_state_source=sea_source,
    )
    brg = initial_bearing_deg(*start, *goal)
    summary.direct_bearing_deg, summary.direct_compass = round(brg), compass_point(brg)
    if not rows:
        summary.reason = "no sea-state forecast could be obtained for the route area"
        summary.direct_distance_km = round(haversine_km(*start, *goal), 1)
        return summary

    sea = _field(rows)
    r: RouteResult = plan_route(
        start, goal, sea, vessel=q.vessel, speed_kt=q.speed_kt, margin_km=q.margin_km
    )
    d = r.direct
    summary.direct_distance_km = d.distance_km
    summary.direct_crosses_border, summary.direct_crosses_land = d.crosses_border, d.crosses_land
    summary.direct_min_imbl_km = d.min_imbl_km
    summary.found, summary.reason, summary.compute_ms = r.found, r.reason, r.compute_ms
    if not r.found:
        return summary

    summary.path, summary.legs = r.path, _legs(r.path)
    summary.distance_km, summary.eta_min = r.distance_km, r.eta_min
    summary.min_imbl_km, summary.avoided_hazard = r.min_imbl_km, r.avoided_hazard
    summary.max_wave_m, summary.period_at_max_wave_s = r.max_wave_m, r.max_period_at_max_wave_s
    summary.max_wind_kt = r.max_wind_kt

    # Evidence: the conditions at every model node the route passes, worst over the window.
    if sea_source == "grid":
        prov, fetched, note_extra = outcome.provenance, outcome.fetched_at, outcome.note
        src_m, src_w = "open_meteo/marine grid", "open_meteo/weather grid"
    else:
        prov, fetched = prov_obs.provenance, prov_obs.fetched_at
        note_extra = (
            "no forecast grid available — the harbour forecast is applied to the whole route"
        )
        src_m, src_w = prov_obs.source, "open_meteo/weather"
    for n in r.nodes:
        lat, lon, t, hs, per, _wf, ws, _wdf, _c, _ct = rows[n]
        where = f"route node {lat:.2f}N {lon:.2f}E"
        note = where + (f"; {note_extra}" if note_extra else "")
        dist = round(_dist_to_path(lat, lon, r.path), 1)
        for var, val, unit, src in (
            ("route_wave_height", hs, "m", src_m),
            ("route_wave_period", per, "s", src_m),
            ("route_wind_speed", ws, "kt", src_w),
        ):
            o = ctx.ledger.add(
                Observation(
                    variable=var,
                    value=round(val, 2),
                    unit=unit,
                    source=src,
                    valid_time=t,
                    fetched_at=fetched,
                    distance_km=dist,
                    confidence=CONFIDENCE[prov],
                    note=note,
                    provenance=prov,
                )
            )
            summary.observation_ids.append(o.id)
    return summary
