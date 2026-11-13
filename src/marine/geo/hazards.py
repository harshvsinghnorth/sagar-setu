"""Cyclone and lightning-warning geometry. Pure functions over parsed feed objects: no
network, no clock, no model — so every rule here is unit-tested with real advisories.

Cyclone: a point is under threat when it lies inside the forecast cone of uncertainty OR
inside the forecast area of >= 60 km/h winds. Testing the cone alone is not enough: replaying
past storms showed harbours beside the track, inside the wind field, that the cone missed.

Lightning: a warned area is a circle with the alert's stated area around its centre (the feed
has no polygon), or the asker's own district when the alert names it.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from shapely.geometry import Point

from marine.geo.geodesy import LocalPlane, haversine_km
from marine.sources.gdacs import Storm
from marine.sources.sachet import Warning

# A storm whose last effect on the point ended this long before the sailing window is treated
# as passed; the sea it leaves behind is the wave and wind forecast's job.
PASSED_AFTER = timedelta(hours=6)


@dataclass(frozen=True)
class CycloneThreat:
    name: str
    agency: str
    advisory: int
    issued: datetime | None
    affected: bool
    hours: float | None  # sailing-window start → first forecast time the area is affected
    arrives: datetime | None
    via: str | None  # "wind field" | "forecast cone"
    track_km: float | None  # closest approach of the forecast track to the point
    closest_time: datetime | None
    passed: bool = False


def _closest_on_track(storm: Storm, lat: float, lon: float) -> tuple[float | None, datetime | None]:
    """Distance (km) and time of the track's closest approach, interpolated along each leg."""
    if not storm.track:
        return None, None
    if len(storm.track) == 1:
        p = storm.track[0]
        return haversine_km(lat, lon, p.lat, p.lon), p.time
    plane = LocalPlane(lat, lon)
    xy = [plane.to_xy(p.lon, p.lat) for p in storm.track]
    best: tuple[float, datetime] | None = None
    for (ax, ay), (bx, by), a, b in zip(xy, xy[1:], storm.track, storm.track[1:], strict=False):
        dx, dy = bx - ax, by - ay
        seg2 = dx * dx + dy * dy
        t = 0.0 if seg2 == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / seg2))
        d = math.hypot(ax + t * dx, ay + t * dy)
        when = a.time + (b.time - a.time) * t
        if best is None or d < best[0]:
            best = (d, when)
    return best


def cyclone_threat(storm: Storm, lat: float, lon: float, window_start: datetime) -> CycloneThreat:
    """Is the point inside the storm's forecast cone or its forecast area of >= 60 km/h winds,
    and from when?

    Tried and rejected (BUILD_LOG Step 41): widening the wind area by the mariner's 1-2-3
    track-error allowance. Replayed over the 4 north Indian Ocean storms since mid-2025 it
    caught no extra affected harbour and raised false DO NOT SAILs from 5 to 12, one of them
    at Kochi, 495 km from a 65 km/h depression.
    """
    pt = Point(lon, lat)
    track_km, closest_time = _closest_on_track(storm, lat, lon)
    base = dict(
        name=storm.name,
        agency=storm.agency,
        advisory=storm.episode_id,
        issued=storm.issued,
        track_km=round(track_km, 1) if track_km is not None else None,
        closest_time=closest_time,
    )
    inside = [i for i, (_, g) in enumerate(storm.radii) if g.contains(pt)]
    in_cone = storm.cone is not None and storm.cone.contains(pt)
    in_swath = storm.swath is not None and storm.swath.contains(pt)
    if not (inside or in_cone or in_swath):
        return CycloneThreat(affected=False, hours=None, arrives=None, via=None, **base)

    if inside:
        # Forecast frames are hours apart: inside frame k but not k-1 means the winds arrive
        # somewhere between them — take the earlier frame (the cautious end).
        first = inside[0]
        arrives = storm.radii[first - 1][0] if first > 0 else storm.radii[0][0]
        last = storm.radii[inside[-1]][0]
        via = "wind field"
    else:
        arrives = last = closest_time or storm.issued or window_start
        via = "forecast cone" if in_cone else "wind field"
    if last < window_start - PASSED_AFTER:
        return CycloneThreat(
            affected=False, hours=None, arrives=arrives, via=via, passed=True, **base
        )
    hours = max(0.0, (arrives - window_start).total_seconds() / 3600.0)
    return CycloneThreat(affected=True, hours=round(hours, 1), arrives=arrives, via=via, **base)


@dataclass(frozen=True)
class WarningHit:
    warning: Warning
    distance_km: float  # point → edge of the warned area; 0 when the area covers the point
    covered: bool
    named: bool  # the alert names the asker's own district


def _names(text: str, district: str | None) -> bool:
    if not district or len(district) < 4:
        return False
    return re.search(rf"\b{re.escape(district)}\b", text, re.IGNORECASE) is not None


def nearest_lightning_warning(
    warnings: list[Warning],
    lat: float,
    lon: float,
    start: datetime,
    end: datetime,
    district: str | None = None,
) -> tuple[WarningHit | None, int]:
    """The official lightning / thunderstorm warning nearest to the point among those in
    force at any time in [start, end], and how many are in force in that window at all."""
    in_force = [w for w in warnings if w.start <= end and w.end >= start]
    best: WarningHit | None = None
    for w in in_force:
        named = _names(w.area_text, district)
        gap = None
        if w.lat is not None and w.lon is not None and w.radius_km is not None:
            gap = haversine_km(lat, lon, w.lat, w.lon) - w.radius_km
        if not named and gap is None:
            continue  # cannot be located at all
        covered = named or (gap is not None and gap <= 0)
        hit = WarningHit(w, 0.0 if covered else round(gap, 1), covered, named)
        if (
            best is None
            or hit.distance_km < best.distance_km
            or (hit.distance_km == best.distance_km and w.end > best.warning.end)
        ):
            best = hit
    return best, len(in_force)
