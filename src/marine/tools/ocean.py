"""Ocean & weather tools. Each fetches through a chain, appends to the ledger, and returns
the observations it added plus what it could not get. Never a bare float."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, Field

from marine.ledger import Observation
from marine.sources.base import PointQuery, SourceUnavailable
from marine.tools.context import ToolContext


class PointWindow(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    start: datetime
    end: datetime


class Point(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class SeriesResult(BaseModel):
    variables: list[str]
    observations: list[Observation]
    missing: list[str] = Field(default_factory=list)  # "variable: reason"
    source_status: dict[str, str] = Field(default_factory=dict)  # source → provenance

    @property
    def ok(self) -> bool:
        return bool(self.observations)


WAVE_VARS = [
    "significant_wave_height",
    "wave_period",
    "wave_direction",
    "swell_height",
    "swell_period",
    "swell_direction",
    "wind_wave_height",
]
WIND_VARS = ["wind_speed", "wind_gust", "wind_direction"]
VIS_VARS = ["visibility", "precipitation", "weather_code", "cape"]
SEA_VARS = ["sea_surface_temperature", "current_speed", "current_direction"]


async def _fetch_vars(
    ctx: ToolContext, chain: str, q: PointQuery, wanted: list[str]
) -> SeriesResult:
    try:
        obs = await ctx.chains[chain].fetch(q)
    except SourceUnavailable as e:
        for v in wanted:
            ctx.ledger.add_missing(v, str(e), ctx.chains[chain].names)
        return SeriesResult(
            variables=wanted, observations=[], missing=[f"{v}: {e}" for v in wanted]
        )
    keep = [o for o in obs if o.variable in wanted]
    added = ctx.ledger.extend(keep)
    got = {o.variable for o in added}
    missing = []
    for v in wanted:
        if v not in got:
            reason = "source returned no values for this variable in the window"
            ctx.ledger.add_missing(v, reason, ctx.chains[chain].names)
            missing.append(f"{v}: {reason}")
    status = {o.source: o.provenance for o in added}
    return SeriesResult(variables=wanted, observations=added, missing=missing, source_status=status)


def _pq(w: PointWindow) -> PointQuery:
    return PointQuery(lat=w.lat, lon=w.lon, start=w.start, end=w.end)


async def get_wave_forecast(ctx: ToolContext, w: PointWindow) -> SeriesResult:
    """Significant wave height, period, direction and swell for the window."""
    return await _fetch_vars(ctx, "marine", _pq(w), WAVE_VARS)


async def get_wind_forecast(ctx: ToolContext, w: PointWindow) -> SeriesResult:
    """10 m wind speed (kt), gusts and direction for the window."""
    return await _fetch_vars(ctx, "weather", _pq(w), WIND_VARS)


async def get_visibility_forecast(ctx: ToolContext, w: PointWindow) -> SeriesResult:
    """Visibility (km), precipitation, WMO weather code and CAPE (convective proxy)."""
    return await _fetch_vars(ctx, "weather", _pq(w), VIS_VARS)


async def get_sea_state(ctx: ToolContext, w: PointWindow) -> SeriesResult:
    """Sea-surface temperature and surface current (kt) for the window."""
    return await _fetch_vars(ctx, "marine", _pq(w), SEA_VARS)


async def get_chlorophyll(ctx: ToolContext, p: Point, days: int = 30) -> SeriesResult:
    """Daily chlorophyll-a for the trailing `days` (VIIRS, ~4 km). Latest value is last."""
    end = datetime.now(UTC)
    q = PointQuery(lat=p.lat, lon=p.lon, start=end - timedelta(days=days), end=end)
    return await _fetch_vars(ctx, "chlorophyll", q, ["chlorophyll_a"])


async def get_argo_temperature(ctx: ToolContext, p: Point) -> SeriesResult:
    """INCOIS Argo 5 m temperature, 1° grid — a coarse cross-check on SST, not a forecast."""
    now = datetime.now(UTC)
    q = PointQuery(lat=p.lat, lon=p.lon, start=now - timedelta(days=60), end=now)
    return await _fetch_vars(ctx, "argo", q, ["sea_temperature_5m"])


async def fan_out(ctx: ToolContext, w: PointWindow) -> dict[str, SeriesResult]:
    """Everything the risk engine needs, fetched concurrently (latency budget: 800 ms warm)."""
    waves, wind, vis, sea = await asyncio.gather(
        get_wave_forecast(ctx, w),
        get_wind_forecast(ctx, w),
        get_visibility_forecast(ctx, w),
        get_sea_state(ctx, w),
    )
    return {"waves": waves, "wind": wind, "visibility": vis, "sea": sea}
