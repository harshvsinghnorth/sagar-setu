"""Great-circle helpers and a local flat projection. Pure functions, no I/O."""

from __future__ import annotations

import math

import numpy as np

EARTH_RADIUS_KM = 6371.0088
NM_PER_KM = 0.539957


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dlmb = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def initial_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compass bearing from point 1 to point 2, 0–360, 0 = north."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


def destination(
    lat: float, lon: float, bearing_deg: float, distance_km: float
) -> tuple[float, float]:
    """Point reached travelling `distance_km` along `bearing_deg` from (lat, lon)."""
    d = distance_km / EARTH_RADIUS_KM
    b = math.radians(bearing_deg)
    p1, l1 = math.radians(lat), math.radians(lon)
    p2 = math.asin(math.sin(p1) * math.cos(d) + math.cos(p1) * math.sin(d) * math.cos(b))
    l2 = l1 + math.atan2(
        math.sin(b) * math.sin(d) * math.cos(p1), math.cos(d) - math.sin(p1) * math.sin(p2)
    )
    return math.degrees(p2), (math.degrees(l2) + 540.0) % 360.0 - 180.0


def compass_point(bearing_deg: float) -> str:
    """16-point compass name — what a fisherman actually uses."""
    names = [
        "N",
        "NNE",
        "NE",
        "ENE",
        "E",
        "ESE",
        "SE",
        "SSE",
        "S",
        "SSW",
        "SW",
        "WSW",
        "W",
        "WNW",
        "NW",
        "NNW",
    ]
    return names[int((bearing_deg + 11.25) // 22.5) % 16]


class LocalPlane:
    """Equirectangular projection centred on a point: (lon, lat) ↔ (x_km, y_km).

    Accurate to well under 1 % within ~300 km of the centre, which is all a small-craft
    query ever needs, and it lets shapely do exact nearest-point and crossing maths in km.
    """

    def __init__(self, lat0: float, lon0: float):
        self.lat0, self.lon0 = lat0, lon0
        self.k = EARTH_RADIUS_KM * math.pi / 180.0
        self.cos0 = math.cos(math.radians(lat0))

    def to_xy(self, lon: float, lat: float) -> tuple[float, float]:
        return (lon - self.lon0) * self.k * self.cos0, (lat - self.lat0) * self.k

    def to_xy_array(self, coords: np.ndarray) -> np.ndarray:
        """coords: (n, 2) array of (lon, lat) → (n, 2) array of (x_km, y_km)."""
        out = np.empty_like(coords, dtype=float)
        out[:, 0] = (coords[:, 0] - self.lon0) * self.k * self.cos0
        out[:, 1] = (coords[:, 1] - self.lat0) * self.k
        return out

    def to_lonlat(self, x: float, y: float) -> tuple[float, float]:
        return self.lon0 + x / (self.k * self.cos0), self.lat0 + y / self.k
