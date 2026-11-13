"""Cyclone and lightning-warning checks for a point and a sailing window.

Fetches the two feeds concurrently (GDACS tropical cyclones, NDMA SACHET warnings), works out
what they mean for the point with the pure geometry in `marine.geo.hazards`, and writes
every number to the ledger. The risk engine reads those observations back; nothing here
decides safety, and no model is involved.

What each ledger variable means:
- active_cyclones             storms active in the north Indian Ocean (its presence is the
                              proof that the cyclone check was made)
- cyclone_cone_hours          hours from the window start until a storm's forecast cone or
                              wind field reaches the point
- cyclone_track_distance_km   closest approach of the forecast track of a storm that does
                              NOT threaten the point
- lightning_warnings_in_force official lightning / thunderstorm warnings in force anywhere
                              in India during the window (proof the warning check was made)
- lightning_warning_distance_km  distance to the nearest warned area; 0 = it covers the point
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

from pydantic import BaseModel, Field

from marine.geo.geodesy import haversine_km
from marine.geo.hazards import cyclone_threat, nearest_lightning_warning
from marine.ledger import Observation
from marine.risk.thresholds import LIGHTNING_WARNING_CAUTION_KM
from marine.sources import gdacs, sachet
from marine.sources.base import CONFIDENCE, FetchOutcome, SourceUnavailable
from marine.tools.context import ToolContext

log = logging.getLogger(__name__)

# Sampled alerts were valid for 1-3 h (BUILD_LOG Step 40): a window that starts later than
# this cannot be covered by any warning issued so far.
NOWCAST_HORIZON = timedelta(hours=3)
REPORT_WITHIN_KM = 100.0  # a warning farther than this is not worth a line in the answer
STRIKES_GAP = (
    "no strike-location feed is available; official lightning warnings and the weather-model "
    "thunderstorm signal were used instead"
)


class HazardQuery(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    start: datetime
    end: datetime
    district: str | None = None  # lets a warning that names the district count as covering


class HazardResult(BaseModel):
    lines: list[str] = Field(default_factory=list)  # fixed-format lines for the brief
    cyclone_checked: bool = False
    lightning_checked: bool = False
    observations: list[Observation] = Field(default_factory=list)


def _obs(
    variable: str,
    value: float,
    unit: str,
    source: str,
    q: HazardQuery,
    outcome: FetchOutcome,
    note: str,
    distance_km: float = 0.0,
) -> Observation:
    note = f"{note}; {outcome.note}" if outcome.note else note
    return Observation(
        variable=variable,
        value=value,
        unit=unit,
        source=source,
        valid_time=q.start,  # computed FOR this sailing window
        fetched_at=outcome.fetched_at,
        distance_km=distance_km,
        confidence=CONFIDENCE[outcome.provenance],
        note=note,
        provenance=outcome.provenance,
        latency_ms=outcome.latency_ms,
    )


async def _cyclones(ctx: ToolContext, q: HazardQuery, res: HazardResult) -> None:
    try:
        feed = await gdacs.fetch_active_storms()
    except SourceUnavailable as e:
        ctx.ledger.add_missing("cyclone", str(e), [gdacs.SOURCE_NAME])
        return
    out: list[Observation] = []
    for name, lat, lon in feed.unresolved:
        d = round(haversine_km(q.lat, q.lon, lat, lon))
        res.lines.append(
            f"cyclone check: {name} is active {d:g} km from this point but its forecast "
            "could not be loaded"
        )
        ctx.ledger.add_missing(
            "cyclone",
            f"{name} is active but its forecast geometry could not be loaded",
            [gdacs.SOURCE_NAME],
        )
        out.append(
            _obs(
                "cyclone_position_distance_km",
                d,
                "km",
                gdacs.SOURCE_NAME,
                q,
                feed.outcome,
                f"{name}: last reported position; forecast not loaded",
                d,
            )
        )
    for storm in feed.storms:
        t = cyclone_threat(storm, q.lat, q.lon, q.start)
        who = f"{t.name}: {t.agency} forecast via GDACS, advisory {t.advisory}"
        far = (
            f"; its forecast track passes {t.track_km:g} km away" if t.track_km is not None else ""
        )
        if t.affected:
            out.append(
                _obs(
                    "cyclone_cone_hours",
                    t.hours,
                    "h",
                    gdacs.SOURCE_NAME,
                    q,
                    feed.outcome,
                    f"{who}; reaches this area {t.arrives:%d %b %H:%M} UTC ({t.via})",
                    t.track_km or 0.0,
                )
            )
            if t.track_km is not None:
                out.append(
                    _obs(
                        "cyclone_track_distance_km",
                        t.track_km,
                        "km",
                        gdacs.SOURCE_NAME,
                        q,
                        feed.outcome,
                        f"{who}; closest approach of the forecast track",
                        t.track_km,
                    )
                )
            when = (
                f"is forecast to affect this area in about {t.hours:g} h"
                if t.hours
                else "is forecast to be affecting this area when the window starts"
            )
            res.lines.append(f"cyclone check: {t.name} {when}{far}")
        else:
            if t.track_km is not None:
                out.append(
                    _obs(
                        "cyclone_track_distance_km",
                        t.track_km,
                        "km",
                        gdacs.SOURCE_NAME,
                        q,
                        feed.outcome,
                        f"{who}; "
                        + (
                            "already past this area"
                            if t.passed
                            else "outside the forecast cone and wind field"
                        ),
                        t.track_km,
                    )
                )
            if t.passed:
                res.lines.append(
                    f"cyclone check: {t.name} has already passed this area"
                    + (
                        f"; its track came within {t.track_km:g} km"
                        if t.track_km is not None
                        else ""
                    )
                )
            else:
                res.lines.append(
                    f"cyclone check: {t.name} is active"
                    + (
                        f"; its forecast track stays {t.track_km:g} km from this point, "
                        if t.track_km is not None
                        else ", "
                    )
                    + "outside the forecast cone and wind field"
                )
    if not feed.unresolved:  # a complete check: only then may the engine read "no threat"
        names = ", ".join(s.name for s in feed.storms)
        out.append(
            _obs(
                "active_cyclones",
                float(len(feed.storms)),
                "count",
                gdacs.SOURCE_NAME,
                q,
                feed.outcome,
                f"active in the north Indian Ocean: {names}"
                if names
                else "no active tropical cyclone in the north Indian Ocean",
            )
        )
        res.cyclone_checked = True
        if not feed.storms:
            res.lines.append("cyclone check: no active tropical cyclone in the north Indian Ocean")
    res.observations += ctx.ledger.extend(out)


async def _lightning(ctx: ToolContext, q: HazardQuery, res: HazardResult) -> None:
    try:
        feed = await sachet.fetch_lightning_warnings()
    except SourceUnavailable as e:
        ctx.ledger.add_missing("lightning_warnings", str(e), [sachet.SOURCE_NAME])
        return
    hit, in_force = nearest_lightning_warning(
        feed.warnings, q.lat, q.lon, q.start, q.end, q.district
    )
    out = [
        _obs(
            "lightning_warnings_in_force",
            float(in_force),
            "count",
            sachet.SOURCE_NAME,
            q,
            feed.outcome,
            "official lightning / thunderstorm warnings in force in India during the window",
        )
    ]
    if hit is not None and hit.distance_km <= REPORT_WITHIN_KM:
        w = hit.warning
        until = w.end.astimezone(sachet.IST)
        out.append(
            _obs(
                "lightning_warning_distance_km",
                hit.distance_km,
                "km",
                sachet.SOURCE_NAME,
                q,
                feed.outcome,
                f"{w.kind}, {w.sender}; in force until {until:%H:%M} IST {until:%d %b}; "
                f"area: {w.area_text[:90]}"
                + ("; names this district" if hit.named else "")
                + "; area approximated as a circle of the stated size",
                hit.distance_km,
            )
        )
        if hit.covered:
            res.lines.append(
                f"lightning check: official {w.kind} warning from {w.sender} covers this area "
                f"until {until:%H:%M} IST"
            )
        else:
            res.lines.append(
                f"lightning check: official {w.kind} warning from {w.sender} is "
                f"{hit.distance_km:g} km away, in force until {until:%H:%M} IST"
            )
    elif in_force == 0 and q.start - feed.outcome.fetched_at > NOWCAST_HORIZON:
        res.lines.append(
            "lightning check: official warnings are issued only a few hours ahead; none can "
            "cover this window yet"
        )
    else:
        res.lines.append(
            "lightning check: no official lightning or thunderstorm warning within "
            f"{LIGHTNING_WARNING_CAUTION_KM:g} km of this point for the window"
        )
    res.lightning_checked = True
    ctx.ledger.add_missing("lightning_strikes", STRIKES_GAP, ["imd"])
    res.observations += ctx.ledger.extend(out)


async def check_hazards(ctx: ToolContext, q: HazardQuery) -> HazardResult:
    """Cyclone threat and official lightning warnings for the point and window. A feed that
    cannot be reached is recorded as missing — it never becomes "no threat"."""
    res = HazardResult()

    async def guarded(fn, variable: str) -> None:
        try:
            await fn(ctx, q, res)
        except Exception as e:  # noqa: BLE001 — a parser surprise degrades, never kills, the answer
            log.exception("hazard check failed: %s", variable)
            ctx.ledger.add_missing(variable, f"check failed: {type(e).__name__}", [])

    await asyncio.gather(guarded(_cyclones, "cyclone"), guarded(_lightning, "lightning_warnings"))
    return res
