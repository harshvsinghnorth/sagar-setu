"""INCOIS Potential Fishing Zone advisory (rule 5: consume, never reimplement).

The public page is prose; INCOIS's own geoportal reads an undocumented GeoServer WFS that
returns the day's PFZ lines as GeoJSON (verified 2026-09-15, docs/data-sources.md). One
global fetch per day, cached. Bearing/distance are computed downstream in `marine.geo.pfz`
because the landing-centre layer's own bearing fields are frozen at 2024-04-27.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from marine.sources.base import FetchOutcome, SourceUnavailable, try_fallback, try_live

PFZ_URL = (
    "https://incois.gov.in/geoserver/PFZ_Automation/ows?service=WFS&version=1.1.0"
    "&request=GetFeature&typeName=PFZ_Automation:pfzlines&outputFormat=application/json"
)
SOURCE_NAME = "incois/pfz"
SNAPSHOT_KEY = "incois_pfz_lines"
TTL = timedelta(hours=6)


@dataclass
class PfzZone:
    uid: str
    state: str
    advisory_date: date
    length_km: float
    coordinates: list[list[tuple[float, float]]]  # MultiLineString: list of (lon, lat) lines


@dataclass
class PfzAdvisory:
    zones: list[PfzZone]
    outcome: FetchOutcome

    @property
    def advisory_date(self) -> date | None:
        return max((z.advisory_date for z in self.zones), default=None)

    def valid_time(self) -> datetime:
        d = self.advisory_date or self.outcome.fetched_at.date()
        return datetime(d.year, d.month, d.day, tzinfo=UTC)


def parse_zones(payload: dict) -> list[PfzZone]:
    zones: list[PfzZone] = []
    for f in payload.get("features") or []:
        p = f.get("properties") or {}
        g = f.get("geometry") or {}
        if g.get("type") != "MultiLineString":
            continue
        try:
            adv = date(int(p["Year"]), 1, 1) + timedelta(days=int(p["Julian_day"]) - 1)
        except (KeyError, ValueError):
            continue
        zones.append(
            PfzZone(
                uid=str(p.get("UID", f.get("id", ""))),
                state=str(p.get("State_Name", "")).strip().upper(),
                advisory_date=adv,
                length_km=float(p.get("Length") or 0.0),
                coordinates=[[(lon, lat) for lon, lat in line] for line in g["coordinates"]],
            )
        )
    return zones


async def fetch_pfz() -> PfzAdvisory:
    """Live (or fresh cache) → stale cache → snapshot. Raises SourceUnavailable if none."""
    out = await try_live(PFZ_URL, TTL)
    if isinstance(out, str):
        fb = try_fallback(PFZ_URL, out, SNAPSHOT_KEY, None, None)
        if fb is None:
            raise SourceUnavailable(f"{SOURCE_NAME}: {out}; no cache, no snapshot")
        out = fb
    return PfzAdvisory(zones=parse_zones(out.payload), outcome=out)
