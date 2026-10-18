"""Safety tools. `assess_sailing_risk` reads worst-case values out of the ledger and hands
them to the deterministic engine; `safety_briefing` is the one-call version that fans out
the fetches first. No model here (CLAUDE.md rule 1)."""

from __future__ import annotations

import time
from datetime import datetime

from pydantic import BaseModel, Field

from marine.ledger import EvidenceLedger
from marine.risk.rules import RiskInputs, RiskVerdict, evaluate
from marine.risk.thresholds import VesselClass
from marine.sources import imd
from marine.tools.context import ToolContext
from marine.tools.ocean import PointWindow, SeriesResult, fan_out
from marine.tools.spatial import HeadingQuery, check_position, predict_boundary_crossing
from marine.tools.windows import describe_window


class RiskQuery(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    start: datetime
    end: datetime
    vessel: VesselClass = VesselClass.TRADITIONAL
    heading_deg: float | None = Field(default=None, ge=0, lt=360)
    speed_kt: float | None = Field(default=None, ge=0, le=40)
    # Ledger ids of route_* observations (plan_sea_route): the verdict then covers the whole
    # trip — the worst of harbour and route — not just the departure point.
    route_obs: list[str] = Field(default_factory=list)


class FeedStatus(BaseModel):
    feed: str
    available: bool
    reason: str


def cyclone_status(ctx: ToolContext) -> FeedStatus:
    """Is there a cyclone-cone feed? Today: no (IMD key). Recorded as a ledger gap."""
    ok = imd.available()
    if not ok:
        ctx.ledger.add_missing("cyclone_cone_hours", imd.missing_reason(), [imd.SOURCE_NAME])
    return FeedStatus(feed="cyclone", available=ok, reason=imd.missing_reason() if not ok else "ok")


def lightning_status(ctx: ToolContext) -> FeedStatus:
    ok = imd.available()
    if not ok:
        ctx.ledger.add_missing("lightning_distance_km", imd.missing_reason(), [imd.SOURCE_NAME])
    return FeedStatus(
        feed="lightning", available=ok, reason=imd.missing_reason() if not ok else "ok"
    )


def _ids(obs) -> list[str]:
    return [o.id for o in obs]


def inputs_from_ledger(ledger: EvidenceLedger, start: datetime, end: datetime) -> RiskInputs:
    """Worst-of over the window: max wave/wind/gust/CAPE, min visibility, the period at the
    time of the highest wave, any thunderstorm code in the window."""
    ev: dict[str, list[str]] = {}
    hs = ledger.worst("significant_wave_height", start, end)
    period = ledger.at("wave_period", hs.valid_time) if hs else None
    wind = ledger.worst("wind_speed", start, end)
    gust = ledger.worst("wind_gust", start, end)
    vis = ledger.worst("visibility", start, end, higher_is_worse=False)
    cape = ledger.worst("cape", start, end)
    codes = ledger.series("weather_code", start, end)
    storm = next((o for o in codes if int(o.value) in (95, 96, 99)), None)
    code_obs = storm or (max(codes, key=lambda o: o.value) if codes else None)
    for k, o in (
        ("wave_height", hs),
        ("wave_period", period),
        ("wind", wind),
        ("gust", gust),
        ("visibility", vis),
        ("cape", cape),
        ("weather_code", code_obs),
    ):
        if o:
            ev[k] = [o.id]
    return RiskInputs(
        wave_height_m=hs.value if hs else None,
        wave_period_s=period.value if period else None,
        wind_kt=wind.value if wind else None,
        gust_kt=gust.value if gust else None,
        visibility_km=vis.value if vis else None,
        cape_jkg=cape.value if cape else None,
        weather_code=int(code_obs.value) if code_obs else None,
        lightning_data_available=imd.available(),
        cyclone_data_available=imd.available(),
        evidence=ev,
    )


def merge_route_conditions(inputs: RiskInputs, ledger: EvidenceLedger, ids: list[str]) -> None:
    """Raise wave and wind to the worst point on the route when that is worse than the
    harbour. The wave period comes from the SAME route node as the worst wave (paired by the
    observation note), so steepness is never computed from two different places."""
    obs = [o for o in (ledger.get(i) for i in ids) if o is not None]
    waves = [o for o in obs if o.variable == "route_wave_height"]
    if waves:
        w = max(waves, key=lambda o: o.value)
        if inputs.wave_height_m is None or w.value > inputs.wave_height_m:
            per = next(
                (o for o in obs if o.variable == "route_wave_period" and o.note == w.note), None
            )
            inputs.wave_height_m = w.value
            inputs.wave_period_s = per.value if per and per.value > 0 else None
            inputs.evidence["wave_height"] = [w.id]
            inputs.evidence["wave_period"] = [per.id] if per else []
    winds = [o for o in obs if o.variable == "route_wind_speed"]
    if winds:
        v = max(winds, key=lambda o: o.value)
        if inputs.wind_kt is None or v.value > inputs.wind_kt:
            inputs.wind_kt = v.value
            inputs.evidence["wind"] = [v.id]


def assess_sailing_risk(ctx: ToolContext, q: RiskQuery) -> RiskVerdict:
    """Deterministic verdict from whatever is already in the ledger for the window.
    Call the fetch tools (or `safety_briefing`) first."""
    inputs = inputs_from_ledger(ctx.ledger, q.start, q.end)
    if q.route_obs:
        merge_route_conditions(inputs, ctx.ledger, q.route_obs)
    pos = check_position(ctx, q)
    inputs.outside_indian_waters = pos.status.zone == "outside_india"
    inputs.boundary_name = pos.status.nearest_imbl.name if pos.status.nearest_imbl else None
    inputs.evidence["boundary"] = _ids(pos.observations)
    if q.heading_deg is not None and q.speed_kt:
        cr = predict_boundary_crossing(
            ctx, HeadingQuery(lat=q.lat, lon=q.lon, heading_deg=q.heading_deg, speed_kt=q.speed_kt)
        )
        if cr.prediction.minutes_to_crossing is not None:
            inputs.boundary_crossing_min = cr.prediction.minutes_to_crossing
            inputs.boundary_horizon_min = cr.prediction.horizon_min
            inputs.boundary_name = cr.prediction.boundary
            inputs.evidence["boundary"] += _ids(cr.observations)
    cyclone_status(ctx)
    lightning_status(ctx)
    return evaluate(inputs, q.vessel)


class SafetyBriefing(BaseModel):
    verdict: RiskVerdict
    window: str
    fetched: dict[str, SeriesResult]
    elapsed_ms: int


async def safety_briefing(ctx: ToolContext, q: RiskQuery) -> SafetyBriefing:
    """Fan out waves/wind/visibility/sea concurrently, then the deterministic verdict."""
    t0 = time.perf_counter()
    fetched = await fan_out(ctx, PointWindow(lat=q.lat, lon=q.lon, start=q.start, end=q.end))
    verdict = assess_sailing_risk(ctx, q)
    return SafetyBriefing(
        verdict=verdict,
        window=describe_window(q.start, q.end),
        fetched=fetched,
        elapsed_ms=round((time.perf_counter() - t0) * 1000),
    )
