"""Tropical cyclones from GDACS (Global Disaster Alert and Coordination System, UN / EU).

No key. Verified 2026-11-04 (docs/data-sources.md, BUILD_LOG Step 40). For every advisory of
every active storm GDACS publishes GeoJSON: the forecast cone of uncertainty, the area of
>= 60 km/h winds (whole swath and per forecast time), and the track positions.

This is the interim cyclone feed while the IMD API key is unavailable. The storm data GDACS
carries for the north Indian Ocean comes from JTWC (US Navy), NOT from IMD, which is the
official centre for this basin — every observation says so.

Two rules that differ from the other sources:
- A cyclone answer may never come from the frozen snapshot or from a cache older than
  MAX_AGE: "no cyclone" from last month is not evidence. Past that age the feed counts as
  unavailable and the verdict says the cyclone check could not be made.
- The geometry call is slow (5.5 s when measured), so it is only made while a storm is
  active in the basin, with its own longer timeout, and cached.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import shapely
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

from marine.sources.base import FetchOutcome, SourceUnavailable, try_fallback, try_live

BASE = "https://www.gdacs.org/gdacsapi/api"
LIST_URL = f"{BASE}/events/geteventlist/SEARCH?eventlist=TC&alertlevel=green;orange;red"
SOURCE_NAME = "gdacs/tc"
TTL = timedelta(minutes=30)
MAX_AGE = timedelta(hours=6)  # advisories are 6-hourly; older than this is not a check
LIST_TIMEOUT_S = 6.0  # measured 1.2-3.4 s
GEOMETRY_TIMEOUT_S = 12.0
# North Indian Ocean with a margin: Arabian Sea, Bay of Bengal, Andaman Sea.
BASIN = (40.0, -5.0, 105.0, 35.0)  # west, south, east, north
RECENT = timedelta(hours=48)  # a "current" event with no advisory for this long has ended


def _utcnow() -> datetime:
    return datetime.now(UTC)  # one place for tests to set the clock


def geometry_url(event_id: int, episode_id: int) -> str:
    return f"{BASE}/polygons/getgeometry?eventtype=TC&eventid={event_id}&episodeid={episode_id}"


@dataclass
class TrackPoint:
    time: datetime
    lat: float
    lon: float


@dataclass
class Storm:
    name: str  # "MURASU-26"
    event_id: int
    episode_id: int  # advisory number
    agency: str  # who made the forecast: "JTWC"
    alert_level: str  # GDACS humanitarian alert colour — not a sea-state measure
    issued: datetime | None = None  # advisory time
    cone: BaseGeometry | None = None  # forecast cone of uncertainty
    swath: BaseGeometry | None = None  # everywhere winds >= 60 km/h, past and forecast
    radii: list[tuple[datetime, BaseGeometry]] = field(default_factory=list)  # >= 60 km/h at t
    track: list[TrackPoint] = field(default_factory=list)


@dataclass
class CycloneFeed:
    storms: list[Storm]
    outcome: FetchOutcome  # of the event list: provenance, fetch time
    # Active storms whose forecast geometry could not be fetched: (name, lat, lon of the last
    # known position). The check is then incomplete and must say so — never "no threat".
    unresolved: list[tuple[str, float, float]] = field(default_factory=list)


def _dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s[:19]).replace(tzinfo=UTC)
    except ValueError:
        return None


def _label_time(label: str, near: datetime) -> datetime | None:
    """'03/11 12:00 UTC' → that day and hour, in the year that puts it closest to `near`."""
    try:
        day, month = int(label[0:2]), int(label[3:5])
        hour, minute = int(label[6:8]), int(label[9:11])
    except (ValueError, IndexError):
        return None
    best = None
    for year in (near.year - 1, near.year, near.year + 1):
        try:
            t = datetime(year, month, day, hour, minute, tzinfo=UTC)
        except ValueError:
            continue
        if best is None or abs(t - near) < abs(best - near):
            best = t
    return best


def active_in_basin(listing: dict, now: datetime) -> list[dict]:
    """Event-list properties of storms that are current, recent, and inside the basin."""
    w, s, e, n = BASIN
    out = []
    for f in listing.get("features") or []:
        p = f.get("properties") or {}
        coords = (f.get("geometry") or {}).get("coordinates") or []
        if len(coords) < 2 or str(p.get("iscurrent")).lower() != "true":
            continue
        last = _dt(p.get("todate"))
        if last is None or now - last > RECENT:
            continue
        if w <= coords[0] <= e and s <= coords[1] <= n:
            out.append({**p, "_lon": coords[0], "_lat": coords[1]})
    return out


def parse_storm(props: dict, geojson: dict) -> Storm:
    """One advisory's GeoJSON → cone, wind field and timed track. Pure."""
    st = Storm(
        name=str(props.get("eventname") or props.get("name") or "unnamed"),
        event_id=int(props["eventid"]),
        episode_id=int(props["episodeid"]),
        agency=str(props.get("source") or "unknown"),
        alert_level=str(props.get("alertlevel") or ""),
    )
    cones, swaths = [], []
    for f in geojson.get("features") or []:
        q = f.get("properties") or {}
        cls = str(q.get("Class") or "")
        try:
            geom = shape(f["geometry"])
        except (KeyError, ValueError, TypeError, AttributeError):
            continue
        if not geom.is_valid:
            geom = shapely.make_valid(geom)
        when = _dt(q.get("polygondate"))
        if cls == "Poly_Cones":
            cones.append(geom)
            st.issued = st.issued or when
        elif cls == "Poly_Green" and q.get("featuretype") == "WindRadii" and when:
            st.radii.append((when, geom))  # for these, polygondate is the forecast time
        elif cls == "Poly_Green" and q.get("featuretype") is None:
            swaths.append(geom)
        elif cls.startswith("Point_Polygon_Point") and when:
            st.issued = st.issued or when  # here polygondate is the advisory time
            t = _label_time(str(q.get("polygonlabel") or ""), when)
            if t is not None:
                c = geom.centroid
                st.track.append(TrackPoint(t, c.y, c.x))
    st.cone = shapely.union_all(cones) if cones else None
    st.swath = shapely.union_all(swaths) if swaths else None
    st.radii.sort(key=lambda r: r[0])
    st.track.sort(key=lambda p: p.time)
    return st


async def _get(url: str, timeout_s: float, now: datetime) -> FetchOutcome:
    """Live or fresh cache, else a cache no older than MAX_AGE. Never the snapshot."""
    out = await try_live(url, TTL, timeout_s)
    if isinstance(out, str):
        fb = try_fallback(url, out, None, None, None)
        if fb is None or now - fb.fetched_at > MAX_AGE:
            raise SourceUnavailable(
                f"{SOURCE_NAME}: {out}; no copy newer than {MAX_AGE.total_seconds() / 3600:g} h"
            )
        out = fb
    return out


async def fetch_active_storms(now: datetime | None = None) -> CycloneFeed:
    """Storms active in the north Indian Ocean with their latest advisory's geometry.
    Raises SourceUnavailable when the event list cannot be had within MAX_AGE."""
    now = now or _utcnow()
    listing = await _get(LIST_URL, LIST_TIMEOUT_S, now)
    feed = CycloneFeed(storms=[], outcome=listing)
    for props in active_in_basin(listing.payload, now):
        ep = int(props["episodeid"])
        geo = None
        # The newest advisory's geometry is sometimes not published yet ("No data found").
        for episode in (ep, ep - 1):
            if episode < 1:
                break
            try:
                g = await _get(
                    geometry_url(int(props["eventid"]), episode), GEOMETRY_TIMEOUT_S, now
                )
            except SourceUnavailable:
                continue
            if isinstance(g.payload, dict) and g.payload.get("features"):
                geo, props = g, {**props, "episodeid": episode}
                break
        if geo is None:
            feed.unresolved.append((str(props.get("eventname")), props["_lat"], props["_lon"]))
            continue
        feed.storms.append(parse_storm(props, geo.payload))
    return feed
