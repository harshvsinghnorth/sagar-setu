"""EEZ / IMBL geofencing, including the predictive version (project the heading forward and
warn *before* the crossing, not after). Static Marine Regions data from data/static/.

The Gulf of Mannar / Palk Bay India–Sri Lanka line is the case that matters: fishermen are
detained there every year.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal

import numpy as np
from shapely.geometry import LineString, MultiPolygon, Point, shape
from shapely.ops import unary_union
from shapely.prepared import prep

from marine.config import STATIC_DIR
from marine.geo.geodesy import LocalPlane, compass_point, destination, initial_bearing_deg

# Marine Regions line_type values that are a maritime boundary with another state.
IMBL_TYPES = {"Treaty", "Median line", "Court ruling"}
KM_PER_NM = 1.852


@dataclass(frozen=True)
class BoundaryLine:
    name: str  # "Sri Lanka - India"
    line_type: str  # "Treaty"
    other_state: str  # "Sri Lanka"
    coords: np.ndarray  # (n, 2) lon/lat


@dataclass(frozen=True)
class NearestBoundary:
    name: str
    other_state: str
    distance_km: float
    bearing_deg: float  # from the query point towards the closest point on the line
    compass: str
    closest_lat: float
    closest_lon: float


Zone = Literal["eez", "land_or_port", "outside_india"]


@dataclass(frozen=True)
class PositionStatus:
    zone: Zone  # at sea inside India's EEZ / on Indian land or internal waters / not Indian
    inside_india_eez: bool
    nearest_imbl: NearestBoundary | None


@dataclass(frozen=True)
class CrossingPrediction:
    """Where and when the projected track meets a boundary, if it does."""

    crosses_within_horizon: bool
    boundary: str | None
    other_state: str | None
    minutes_to_crossing: float | None
    distance_to_crossing_km: float | None
    crossing_lat: float | None
    crossing_lon: float | None
    horizon_min: float
    track: list[tuple[float, float]]  # (lat, lon) samples of the projected track


@lru_cache(maxsize=1)
def load_imbl() -> list[BoundaryLine]:
    data = json.loads((STATIC_DIR / "india_eez_boundaries.geojson").read_text(encoding="utf-8"))
    lines: list[BoundaryLine] = []
    for f in data["features"]:
        p = f["properties"]
        if p.get("line_type") not in IMBL_TYPES:
            continue
        g = f["geometry"]
        parts = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
        other = p.get("sovereign2") if p.get("sovereign1") == "India" else p.get("sovereign1")
        for part in parts:
            if len(part) >= 2:
                lines.append(
                    BoundaryLine(
                        p["line_name"],
                        p["line_type"],
                        other or "?",
                        np.asarray(part, dtype=float)[:, :2],
                    )
                )
    return lines


@lru_cache(maxsize=1)
def load_eez() -> MultiPolygon:
    """India's EEZ: mainland + Lakshadweep (mrgid 8480) and Andaman & Nicobar (mrgid 8333) —
    Marine Regions publishes them as separate polygons."""
    data = json.loads((STATIC_DIR / "india_eez_polygon.geojson").read_text(encoding="utf-8"))
    eez = unary_union([shape(f["geometry"]) for f in data["features"]])
    return eez if isinstance(eez, MultiPolygon) else MultiPolygon([eez])


@lru_cache(maxsize=1)
def _eez_prepared():
    return prep(load_eez())


@lru_cache(maxsize=1)
def load_india_union():
    """EEZ + land union (Marine Regions eez_land): 'is this point Indian at all?'"""
    data = json.loads((STATIC_DIR / "india_eez_land_union.geojson").read_text(encoding="utf-8"))
    return unary_union([shape(f["geometry"]) for f in data["features"]])


@lru_cache(maxsize=1)
def _india_union_prepared():
    return prep(load_india_union())


@lru_cache(maxsize=1)
def _eez_rings() -> list[np.ndarray]:
    rings: list[np.ndarray] = []
    for poly in load_eez().geoms:
        rings.append(np.asarray(poly.exterior.coords, dtype=float)[:, :2])
    return rings


def inside_india_eez(lat: float, lon: float) -> bool:
    return bool(_eez_prepared().contains(Point(lon, lat)))


def nearest_imbl(lat: float, lon: float) -> NearestBoundary | None:
    plane = LocalPlane(lat, lon)
    origin = Point(0.0, 0.0)
    best: tuple[float, BoundaryLine, Point] | None = None
    for line in load_imbl():
        ls = LineString(plane.to_xy_array(line.coords))
        d = ls.distance(origin)
        if best is None or d < best[0]:
            best = (d, line, ls.interpolate(ls.project(origin)))
    if best is None:
        return None
    d, line, pt = best
    c_lon, c_lat = plane.to_lonlat(pt.x, pt.y)
    brg = initial_bearing_deg(lat, lon, c_lat, c_lon)
    return NearestBoundary(
        line.name,
        line.other_state,
        round(d, 1),
        round(brg),
        compass_point(brg),
        round(c_lat, 4),
        round(c_lon, 4),
    )


def position_status(lat: float, lon: float) -> PositionStatus:
    pt = Point(lon, lat)
    in_eez = bool(_eez_prepared().contains(pt))
    if in_eez:
        zone: Zone = "eez"
    elif _india_union_prepared().contains(pt):
        zone = "land_or_port"
    else:
        zone = "outside_india"
    return PositionStatus(zone, in_eez, nearest_imbl(lat, lon))


def project_track(
    lat: float,
    lon: float,
    heading_deg: float,
    speed_kt: float,
    minutes: float,
    step_min: float = 5.0,
) -> list[tuple[float, float]]:
    pts = [(lat, lon)]
    t = step_min
    while t <= minutes + 1e-9:
        pts.append(destination(lat, lon, heading_deg, speed_kt * KM_PER_NM * t / 60.0))
        t += step_min
    return pts


def predict_crossing(
    lat: float,
    lon: float,
    heading_deg: float,
    speed_kt: float,
    horizon_min: float = 90.0,
    lookahead_min: float = 720.0,
) -> CrossingPrediction:
    """Project the vessel along its heading and find the first IMBL / EEZ-edge crossing.

    We look ahead `lookahead_min` (12 h) so the answer can say "you reach the line in 2 h 40"
    even when it is beyond the 90 min warning horizon; `crosses_within_horizon` is the flag
    the risk engine and UI act on.
    """
    track = project_track(lat, lon, heading_deg, speed_kt, horizon_min)
    if speed_kt <= 0:
        return CrossingPrediction(False, None, None, None, None, None, None, horizon_min, track)
    plane = LocalPlane(lat, lon)
    reach_km = speed_kt * KM_PER_NM * lookahead_min / 60.0
    end_lat, end_lon = destination(lat, lon, heading_deg, reach_km)
    path = LineString([(0.0, 0.0), plane.to_xy(end_lon, end_lat)])

    candidates: list[tuple[float, str, str, Point]] = []
    for line in load_imbl():
        hit = path.intersection(LineString(plane.to_xy_array(line.coords)))
        if not hit.is_empty:
            for g in getattr(hit, "geoms", [hit]):
                p = g if g.geom_type == "Point" else Point(g.coords[0])
                candidates.append((path.project(p), line.name, line.other_state, p))
    for ring in _eez_rings():
        hit = path.intersection(LineString(plane.to_xy_array(ring)))
        if not hit.is_empty:
            for g in getattr(hit, "geoms", [hit]):
                p = g if g.geom_type == "Point" else Point(g.coords[0])
                candidates.append((path.project(p), "India EEZ outer limit", "high seas", p))
    if not candidates:
        return CrossingPrediction(False, None, None, None, None, None, None, horizon_min, track)
    d_km, name, other, p = min(candidates, key=lambda c: c[0])
    if d_km < 0.05:  # already on the line — ignore the point we are standing on
        rest = [c for c in candidates if c[0] >= 0.05]
        if not rest:
            return CrossingPrediction(False, None, None, None, None, None, None, horizon_min, track)
        d_km, name, other, p = min(rest, key=lambda c: c[0])
    minutes = d_km / (speed_kt * KM_PER_NM) * 60.0
    c_lon, c_lat = plane.to_lonlat(p.x, p.y)
    return CrossingPrediction(
        crosses_within_horizon=minutes <= horizon_min,
        boundary=name,
        other_state=other,
        minutes_to_crossing=round(minutes, 1),
        distance_to_crossing_km=round(d_km, 1),
        crossing_lat=round(c_lat, 4),
        crossing_lon=round(c_lon, 4),
        horizon_min=horizon_min,
        track=track,
    )
