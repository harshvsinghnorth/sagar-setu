"""Official warnings from SACHET, NDMA's national Common Alerting Protocol portal.

No key. Verified 2026-11-04 (docs/data-sources.md, BUILD_LOG Step 40). The active-alerts
endpoint returns every warning in force in India as JSON; the lightning and thunderstorm
ones are issued by IMD's regional offices and by state disaster authorities.

What this is and is not:
- These are WARNINGS (a forecast that lightning is expected over an area in the next few
  hours), not observed strikes. Strike locations are still not available to us.
- Alerts sampled were valid for 1-3 h, so they only speak to a window that starts soon.
- Areas are land districts / sub-districts. There is no polygon: each alert gives a centre
  point and an area, so the warned area is approximated as a circle of that area.
- Like the cyclone feed, never served from the snapshot or from a copy older than MAX_AGE:
  these warnings are reissued continuously.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone

from marine.sources.base import FetchOutcome, SourceUnavailable, try_fallback, try_live

ALERTS_URL = "https://sachet.ndma.gov.in/cap_public_website/FetchAllAlertDetails"
SOURCE_NAME = "ndma/sachet"
TTL = timedelta(minutes=10)
MAX_AGE = timedelta(minutes=45)
TIMEOUT_S = 4.0
IST = timezone(timedelta(hours=5, minutes=30))
LIGHTNING = re.compile(r"lightning|thunder", re.IGNORECASE)
_MONTHS = {
    m: i + 1
    for i, m in enumerate(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    )
}
_WHEN = re.compile(r"^\w{3} (\w{3}) (\d{1,2}) (\d{2}):(\d{2}):(\d{2}) IST (\d{4})$")


def _utcnow() -> datetime:
    return datetime.now(UTC)  # one place for tests to set the clock


@dataclass
class Warning:
    kind: str  # "Thunderstorm with Lightning"
    sender: str  # "IMD Chennai", "Andhra Pradesh SDMA"
    start: datetime
    end: datetime
    area_text: str  # district / sub-district names as issued
    lat: float | None  # centre of the warned area
    lon: float | None
    radius_km: float | None  # radius of the circle with the alert's stated area


@dataclass
class WarningFeed:
    warnings: list[Warning]  # lightning / thunderstorm only
    outcome: FetchOutcome


def parse_when(s: str) -> datetime | None:
    """'Wed Nov 04 09:40:00 IST 2026' → aware datetime. None if the shape is different."""
    m = _WHEN.match((s or "").strip())
    if not m or m.group(1) not in _MONTHS:
        return None
    mon, day, hh, mm, ss, year = m.groups()
    try:
        return datetime(int(year), _MONTHS[mon], int(day), int(hh), int(mm), int(ss), tzinfo=IST)
    except ValueError:
        return None


def parse_alerts(payload: list) -> list[Warning]:
    """Lightning / thunderstorm warnings with usable times. Pure; skips what it cannot read."""
    out: list[Warning] = []
    for r in payload if isinstance(payload, list) else []:
        kind = str(r.get("disaster_type") or "")
        if not LIGHTNING.search(kind):
            continue
        start, end = (
            parse_when(r.get("effective_start_time")),
            parse_when(r.get("effective_end_time")),
        )
        if start is None or end is None or end <= start:
            continue
        lat = lon = radius = None
        try:
            lon_s, lat_s = str(r.get("centroid")).split(",")
            lat, lon = float(lat_s), float(lon_s)
            area = float(r.get("area_covered"))
            radius = math.sqrt(area / math.pi) if area > 0 else None
        except (ValueError, TypeError):
            lat = lon = radius = None
        if radius is None or not (-90 <= (lat or 0) <= 90):
            lat = lon = radius = None
        out.append(
            Warning(
                kind=kind.strip(),
                sender=str(r.get("alert_source") or "unknown").strip(),
                start=start,
                end=end,
                area_text=str(r.get("area_description") or "").strip(),
                lat=lat,
                lon=lon,
                radius_km=radius,
            )
        )
    return out


async def fetch_lightning_warnings(now: datetime | None = None) -> WarningFeed:
    """Live or fresh cache, else a cache no older than MAX_AGE. Never the snapshot."""
    now = now or _utcnow()
    out = await try_live(ALERTS_URL, TTL, TIMEOUT_S)
    if isinstance(out, str):
        fb = try_fallback(ALERTS_URL, out, None, None, None)
        if fb is None or now - fb.fetched_at > MAX_AGE:
            raise SourceUnavailable(
                f"{SOURCE_NAME}: {out}; no copy newer than {MAX_AGE.total_seconds() / 60:g} min"
            )
        out = fb
    return WarningFeed(warnings=parse_alerts(out.payload), outcome=out)
