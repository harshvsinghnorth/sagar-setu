"""INCOIS ERDDAP. Verified 2026-09-15: only the Argo gridded T/S fields are current
(1° grid, 10-day, latest ~6 weeks old, null on coastal cells). Everything else on the
server stopped between 2006 and 2023. This is a weak cross-check, and the ledger says so
through distance_km and fetched_at/valid_time.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from marine.ledger import Observation
from marine.sources.base import JsonSource, PointQuery, haversine_km
from marine.sources.noaa_chl import griddap


class IncoisArgoTemperature(JsonSource):
    name = "incois_erddap/argo_10d"
    snapshot_key = "incois_argo_temp"
    ttl = timedelta(days=1)
    base_confidence = 0.6  # coarse grid, long latency

    def url(self, q: PointQuery) -> str:
        return griddap(
            "https://erddap.incois.gov.in/erddap/griddap/incois_argo_10d_VAM.json"
            f"?TEMP[(last)][(5)][({q.lat})][({q.lon})]"  # top level is 5 m
        )

    def parse(self, payload: dict, q: PointQuery) -> list[Observation]:
        table = payload.get("table") or {}
        cols = table.get("columnNames") or []
        out: list[Observation] = []
        for row in table.get("rows") or []:
            rec = dict(zip(cols, row, strict=False))
            if rec.get("TEMP") is None:
                continue
            t = datetime.fromisoformat(rec["time"].replace("Z", "+00:00")).astimezone(UTC)
            out.append(
                Observation(
                    variable="sea_temperature_5m",
                    value=round(float(rec["TEMP"]), 2),
                    unit="degC",
                    source="",
                    valid_time=t,
                    fetched_at=datetime.now(UTC),
                    distance_km=round(
                        haversine_km(q.lat, q.lon, rec["latitude"], rec["longitude"]), 1
                    ),
                    confidence=1.0,
                    note="Argo 10-day gridded analysis, 1 degree grid",
                )
            )
        return out
