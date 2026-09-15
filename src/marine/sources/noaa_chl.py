"""NOAA CoastWatch VIIRS chlorophyll-a (gap-filled, daily, ~4 km). Open substitute for
Copernicus BGC. Needs a real User-Agent and percent-encoded brackets (docs/data-sources.md).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from marine.ledger import Observation
from marine.sources.base import JsonSource, PointQuery, haversine_km

DATASET = "noaacwNPPN20VIIRSDINEOFDaily"


def griddap(url: str) -> str:
    """ERDDAP griddap needs literal brackets percent-encoded for Tomcat."""
    return url.replace("[", "%5B").replace("]", "%5D")


class NoaaViirsChlorophyll(JsonSource):
    name = "noaa_coastwatch/viirs_chl"
    snapshot_key = "noaa_viirs_chl"
    ttl = timedelta(hours=12)
    base_confidence = 0.9  # gap-filled product: some pixels are interpolated

    def url(self, q: PointQuery) -> str:
        # Request the trailing 30 days so the same URL serves a baseline and the latest value.
        start = (q.end - timedelta(days=30)).strftime("%Y-%m-%dT12:00:00Z")
        return griddap(
            f"https://coastwatch.noaa.gov/erddap/griddap/{DATASET}.json"
            f"?chlor_a[({start}):(last)][(0.0)][({q.lat})][({q.lon})]"
        )

    def parse(self, payload: dict, q: PointQuery) -> list[Observation]:
        table = payload.get("table") or {}
        cols = table.get("columnNames") or []
        out: list[Observation] = []
        for row in table.get("rows") or []:
            rec = dict(zip(cols, row, strict=False))
            if rec.get("chlor_a") is None:
                continue
            t = datetime.fromisoformat(rec["time"].replace("Z", "+00:00")).astimezone(UTC)
            out.append(
                Observation(
                    variable="chlorophyll_a",
                    value=round(float(rec["chlor_a"]), 3),
                    unit="mg/m3",
                    source="",
                    valid_time=t,
                    fetched_at=datetime.now(UTC),
                    distance_km=round(
                        haversine_km(q.lat, q.lon, rec["latitude"], rec["longitude"]), 1
                    ),
                    confidence=1.0,
                )
            )
        return out
