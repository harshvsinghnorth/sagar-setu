"""The four specialists (CLAUDE.md rule 4). Three of them are plain Python over the tool
belt; only Synthesis & Verify (synthesis.py) touches the model.

Each specialist returns a small typed `Finding` — what it learned, what it could not get —
and everything numeric it learned is already in the ledger via the tools it called.
"""

from __future__ import annotations

import statistics
from datetime import datetime

from pydantic import BaseModel, Field

from marine.agents.planner import Plan
from marine.geo.boundaries import CrossingPrediction, PositionStatus
from marine.geo.pfz import PfzHit
from marine.ledger import Observation
from marine.risk.rules import RiskVerdict
from marine.tools import (
    HeadingQuery,
    Point,
    PointWindow,
    RiskQuery,
    ToolContext,
    assess_sailing_risk,
    check_position,
    fan_out,
    get_chlorophyll,
    get_pfz_advisory,
    predict_boundary_crossing,
)
from marine.tools.windows import named_window


class OceanFinding(BaseModel):
    """Ocean & Weather: worst-of summary over the window, sources, disagreements."""

    window_start: datetime
    window_end: datetime
    summary: dict[str, Observation] = Field(default_factory=dict)  # variable → worst obs
    missing: list[str] = Field(default_factory=list)
    disagreements: list[str] = Field(default_factory=list)
    sources: dict[str, str] = Field(default_factory=dict)


class GeoFinding(BaseModel):
    position: PositionStatus | None = None
    pfz_date: str | None = None
    pfz: list[PfzHit] = Field(default_factory=list)
    pfz_note: str | None = None
    crossing: CrossingPrediction | None = None


class AnalyticsFinding(BaseModel):
    """Analytics & Causal: anomaly vs baseline, with the mechanism named but never asserted
    as cause — the data cannot support causation (CLAUDE.md)."""

    latest: Observation | None = None
    baseline_days: int = 0
    baseline_mean: float | None = None
    baseline_sd: float | None = None
    z_score: float | None = None
    trend: str | None = None  # "rising" | "falling" | "flat"
    interpretation: str | None = None
    missing: list[str] = Field(default_factory=list)


def window_for(plan: Plan) -> tuple[datetime, datetime]:
    return named_window(plan.day, plan.part)


async def ocean_weather(ctx: ToolContext, plan: Plan) -> OceanFinding:
    """Fan out waves / wind / visibility / sea concurrently; summarise worst-of per variable."""
    assert plan.location is not None
    start, end = window_for(plan)
    res = await fan_out(
        ctx, PointWindow(lat=plan.location.lat, lon=plan.location.lon, start=start, end=end)
    )
    f = OceanFinding(window_start=start, window_end=end)
    lower_is_worse = {"visibility"}
    for r in res.values():
        f.missing += r.missing
        f.sources.update(r.source_status)
    for var in (
        "significant_wave_height",
        "wave_period",
        "swell_height",
        "swell_period",
        "wind_speed",
        "wind_gust",
        "wind_direction",
        "visibility",
        "cape",
        "weather_code",
        "sea_surface_temperature",
        "current_speed",
        "current_direction",
    ):
        o = ctx.ledger.worst(var, start, end, higher_is_worse=var not in lower_is_worse)
        if o:
            f.summary[var] = o
    # Disagreement flagging: when two sources report the same variable in the window and
    # differ materially, say so rather than average (rule for this agent). Today only one
    # live source per variable exists; the hook is here for Copernicus SST/currents.
    by_var: dict[str, dict[str, float]] = {}
    for o in ctx.ledger.series("sea_surface_temperature", start, end):
        by_var.setdefault(o.variable, {})[o.source] = o.value
    for var, srcs in by_var.items():
        if len(srcs) > 1:
            vals = list(srcs.values())
            if max(vals) - min(vals) > 1.0:
                f.disagreements.append(
                    f"{var}: " + ", ".join(f"{s} {v:g}" for s, v in srcs.items())
                )
    return f


async def geospatial(ctx: ToolContext, plan: Plan) -> GeoFinding:
    """PFZ bearing/distance, position vs IMBL/EEZ, predictive crossing if heading known."""
    assert plan.location is not None
    p = Point(lat=plan.location.lat, lon=plan.location.lon)
    pfz = await get_pfz_advisory(ctx, p)
    pos = check_position(ctx, p)
    f = GeoFinding(
        position=pos.status, pfz_date=pfz.advisory_date, pfz=pfz.zones, pfz_note=pfz.note
    )
    if plan.heading_deg is not None and plan.speed_kt:
        f.crossing = predict_boundary_crossing(
            ctx,
            HeadingQuery(
                lat=p.lat, lon=p.lon, heading_deg=plan.heading_deg, speed_kt=plan.speed_kt
            ),
        ).prediction
    return f


async def analytics(ctx: ToolContext, plan: Plan, days: int = 30) -> AnalyticsFinding:
    """Chlorophyll now vs the trailing baseline. Names a mechanism only as a hypothesis."""
    assert plan.location is not None
    res = await get_chlorophyll(ctx, Point(lat=plan.location.lat, lon=plan.location.lon), days=days)
    f = AnalyticsFinding(missing=res.missing)
    series = sorted(res.observations, key=lambda o: o.valid_time)
    if len(series) < 5:
        f.missing.append("chlorophyll_a: fewer than 5 days in the baseline window")
        return f
    latest = series[-1]
    base = [o.value for o in series[:-1]]
    mean, sd = statistics.fmean(base), statistics.pstdev(base)
    f.latest, f.baseline_days, f.baseline_mean, f.baseline_sd = (
        latest,
        len(base),
        round(mean, 3),
        round(sd, 3),
    )
    f.z_score = round((latest.value - mean) / sd, 2) if sd > 1e-6 else 0.0
    recent = [o.value for o in series[-7:]]
    earlier = [o.value for o in series[-14:-7]] or recent
    delta = statistics.fmean(recent) - statistics.fmean(earlier)
    f.trend = (
        "rising"
        if delta > 0.1 * max(mean, 1e-6)
        else "falling"
        if delta < -0.1 * max(mean, 1e-6)
        else "flat"
    )
    if f.z_score >= 1.5:
        f.interpretation = "chlorophyll is well above its recent baseline — consistent with upwelling or river/runoff input; higher plankton often precedes better catches, but this is an association, not a guarantee"
    elif f.z_score <= -1.5:
        f.interpretation = "chlorophyll is well below its recent baseline — consistent with stratified, nutrient-poor surface water; lower productivity is one possible contributor to a poorer catch, not a proven cause"
    else:
        f.interpretation = "chlorophyll is within its normal recent range — the data does not point to a productivity change as an explanation"
    return f


def risk(ctx: ToolContext, plan: Plan) -> RiskVerdict:
    """The deterministic verdict. Not an agent — a function — but it sits in the DAG."""
    assert plan.location is not None
    start, end = window_for(plan)
    q = RiskQuery(
        lat=plan.location.lat,
        lon=plan.location.lon,
        start=start,
        end=end,
        vessel=plan.vessel or RiskQuery.model_fields["vessel"].default,
        heading_deg=plan.heading_deg,
        speed_kt=plan.speed_kt,
    )
    return assess_sailing_risk(ctx, q)
