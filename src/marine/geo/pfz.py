"""Bearing and distance from a harbour to INCOIS's PFZ lines. Geometry only — the zones
themselves are INCOIS's product (rule 5); we never predict them."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from shapely.geometry import LineString, Point

from marine.geo.geodesy import LocalPlane, compass_point, initial_bearing_deg
from marine.sources.incois_pfz import PfzZone


@dataclass(frozen=True)
class PfzHit:
    uid: str
    state: str
    advisory_date: str  # ISO date
    distance_km: float  # from query point to the nearest point on the zone line
    bearing_deg: float
    compass: str
    nearest_lat: float
    nearest_lon: float
    length_km: float
    coordinates: list[list[tuple[float, float]]]  # (lon, lat) lines, for the map


def nearest_zones(
    lat: float, lon: float, zones: list[PfzZone], k: int = 3, max_km: float = 150.0
) -> list[PfzHit]:
    """The k closest PFZ lines within max_km, nearest first. Empty list = no advisory near here."""
    plane = LocalPlane(lat, lon)
    origin = Point(0.0, 0.0)
    hits: list[PfzHit] = []
    for z in zones:
        best_d, best_pt = None, None
        for part in z.coordinates:
            if len(part) < 2:
                continue
            ls = LineString(plane.to_xy_array(np.asarray(part, dtype=float)))
            d = ls.distance(origin)
            if best_d is None or d < best_d:
                best_d, best_pt = d, ls.interpolate(ls.project(origin))
        if best_d is None or best_d > max_km:
            continue
        n_lon, n_lat = plane.to_lonlat(best_pt.x, best_pt.y)
        brg = initial_bearing_deg(lat, lon, n_lat, n_lon)
        hits.append(
            PfzHit(
                uid=z.uid,
                state=z.state,
                advisory_date=z.advisory_date.isoformat(),
                distance_km=round(best_d, 1),
                bearing_deg=round(brg),
                compass=compass_point(brg),
                nearest_lat=round(n_lat, 4),
                nearest_lon=round(n_lon, 4),
                length_km=round(z.length_km, 1),
                coordinates=z.coordinates,
            )
        )
    hits.sort(key=lambda h: h.distance_km)
    return hits[:k]
