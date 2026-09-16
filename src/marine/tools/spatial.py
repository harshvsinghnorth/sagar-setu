"""Geospatial & boundary tools: PFZ bearing/distance, position vs IMBL/EEZ, predictive
crossing. Geometry results are also written to the ledger as observations so the answer
can cite "42 km SW" with provenance like any other number."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from marine.geo.boundaries import (
    CrossingPrediction,
    NearestBoundary,
    PositionStatus,
    position_status,
    predict_crossing,
)
from marine.geo.pfz import PfzHit, nearest_zones
from marine.ledger import Observation
from marine.sources import incois_pfz
from marine.sources.base import SourceUnavailable
from marine.tools.context import ToolContext
from marine.tools.ocean import Point


class PfzResult(BaseModel):
    advisory_date: str | None
    zones: list[PfzHit]
    observations: list[Observation]
    note: str | None = None
    source_status: str | None = None


class PositionResult(BaseModel):
    status: PositionStatus
    observations: list[Observation]


class HeadingQuery(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    heading_deg: float = Field(ge=0, lt=360)
    speed_kt: float = Field(ge=0, le=40)
    horizon_min: float = Field(default=90.0, gt=0, le=720)


class CrossingResult(BaseModel):
    prediction: CrossingPrediction
    observations: list[Observation]


def _geo_obs(
    variable: str,
    value: float,
    unit: str,
    source: str,
    valid: datetime,
    note: str | None = None,
    confidence: float = 1.0,
    provenance="live",
) -> Observation:
    return Observation(
        variable=variable,
        value=value,
        unit=unit,
        source=source,
        valid_time=valid,
        fetched_at=datetime.now(UTC),
        distance_km=0.0,
        confidence=confidence,
        note=note,
        provenance=provenance,
    )


async def get_pfz_advisory(ctx: ToolContext, p: Point, k: int = 3) -> PfzResult:
    """Nearest INCOIS PFZ lines to the point with our computed bearing and distance."""
    try:
        adv = await incois_pfz.fetch_pfz()
    except SourceUnavailable as e:
        ctx.ledger.add_missing("pfz_distance_km", str(e), [incois_pfz.SOURCE_NAME])
        return PfzResult(advisory_date=None, zones=[], observations=[], note=str(e))
    hits = nearest_zones(p.lat, p.lon, adv.zones, k=k)
    valid = adv.valid_time()
    prov = adv.outcome.provenance
    conf = {"live": 1.0, "cache": 0.95, "stale_cache": 0.7, "snapshot": 0.5}[prov]
    obs: list[Observation] = []
    if not hits:
        ctx.ledger.add_missing(
            "pfz_distance_km",
            f"no PFZ advisory within 150 km on {adv.advisory_date}",
            [incois_pfz.SOURCE_NAME],
        )
        return PfzResult(
            advisory_date=adv.advisory_date.isoformat() if adv.advisory_date else None,
            zones=[],
            observations=[],
            note=f"INCOIS issued no PFZ near this point for {adv.advisory_date}",
            source_status=prov,
        )
    for i, h in enumerate(hits):
        tag = f"pfz#{i + 1} {h.state} {h.uid}"
        obs.append(
            _geo_obs(
                "pfz_distance_km",
                h.distance_km,
                "km",
                incois_pfz.SOURCE_NAME,
                valid,
                f"{tag}; {adv.outcome.note or ''}".strip("; "),
                conf,
                prov,
            )
        )
        obs.append(
            _geo_obs(
                "pfz_bearing_deg",
                h.bearing_deg,
                "deg",
                incois_pfz.SOURCE_NAME,
                valid,
                f"{tag} {h.compass}",
                conf,
                prov,
            )
        )
    ctx.ledger.extend(obs)
    return PfzResult(
        advisory_date=adv.advisory_date.isoformat() if adv.advisory_date else None,
        zones=hits,
        observations=obs,
        note=adv.outcome.note,
        source_status=prov,
    )


def check_position(ctx: ToolContext, p: Point) -> PositionResult:
    """Inside the EEZ / on land / outside Indian waters, and the nearest IMBL."""
    s = position_status(p.lat, p.lon)
    now = datetime.now(UTC)
    obs: list[Observation] = []
    n: NearestBoundary | None = s.nearest_imbl
    if n:
        obs.append(
            _geo_obs(
                "imbl_distance_km",
                n.distance_km,
                "km",
                "marine_regions/eez_boundaries",
                now,
                f"{n.name} ({n.other_state}) {n.compass}",
            )
        )
        obs.append(
            _geo_obs(
                "imbl_bearing_deg",
                n.bearing_deg,
                "deg",
                "marine_regions/eez_boundaries",
                now,
                n.name,
            )
        )
    obs.append(
        _geo_obs(
            "inside_india_eez",
            1.0 if s.inside_india_eez else 0.0,
            "bool",
            "marine_regions/eez",
            now,
            s.zone,
        )
    )
    ctx.ledger.extend(obs)
    return PositionResult(status=s, observations=obs)


def predict_boundary_crossing(ctx: ToolContext, h: HeadingQuery) -> CrossingResult:
    """Project heading and speed forward; warn before an IMBL / EEZ crossing, not after."""
    c = predict_crossing(h.lat, h.lon, h.heading_deg, h.speed_kt, h.horizon_min)
    now = datetime.now(UTC)
    obs: list[Observation] = []
    if c.minutes_to_crossing is not None:
        note = f"{c.boundary} ({c.other_state}) at heading {h.heading_deg:g}°, {h.speed_kt:g} kt"
        obs.append(
            _geo_obs(
                "boundary_crossing_min",
                c.minutes_to_crossing,
                "min",
                "marine_regions/eez_boundaries",
                now,
                note,
            )
        )
        obs.append(
            _geo_obs(
                "boundary_crossing_km",
                c.distance_to_crossing_km,
                "km",
                "marine_regions/eez_boundaries",
                now,
                note,
            )
        )
    ctx.ledger.extend(obs)
    return CrossingResult(prediction=c, observations=obs)
