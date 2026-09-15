"""The deterministic safety verdict (CLAUDE.md rule 1).

Plain Python over plain numbers. No model anywhere near this file. The LLM receives the
`RiskVerdict` and explains it; it does not compute, adjust or soften it.

Worst-of wins. Never average. One no-go parameter makes the whole verdict no-go.
A missing critical parameter (wave height, wind) can never produce GO.
"""

from __future__ import annotations

import time
from typing import Literal

from pydantic import BaseModel, Field

from marine.risk.thresholds import (
    CALIBRATION,
    CAPE_CAUTION_JKG,
    TABLES,
    THUNDERSTORM_CODES,
    Band,
    Level,
    Thresholds,
    VesselClass,
)

CRITICAL = ("wave_height", "wind")


class RiskInputs(BaseModel):
    """Worst-case values over the sailing window. None = we do not have it."""

    wave_height_m: float | None = None
    wave_period_s: float | None = None
    wind_kt: float | None = None
    gust_kt: float | None = None
    visibility_km: float | None = None
    # Lightning: nearest strike distance if a lightning feed exists.
    lightning_km: float | None = None
    lightning_closing: bool | None = None
    lightning_data_available: bool = False
    # Cyclone: hours until the cone of uncertainty intersects the area; None = no intersect.
    cyclone_hours: float | None = None
    cyclone_data_available: bool = False
    # Convective proxies from the weather model (used only when no lightning feed).
    weather_code: int | None = None
    cape_jkg: float | None = None
    # Predictive geofence: minutes until the projected track crosses an IMBL / EEZ edge.
    boundary_crossing_min: float | None = None
    boundary_horizon_min: float = 90.0
    outside_indian_waters: bool | None = None
    boundary_name: str | None = None
    # parameter name → ledger observation ids that produced the value
    evidence: dict[str, list[str]] = Field(default_factory=dict)


class ParameterVerdict(BaseModel):
    parameter: str
    status: Literal["evaluated", "proxy", "missing"]
    level: Level | None
    value: float | None = None
    unit: str | None = None
    caution_at: float | None = None
    no_go_at: float | None = None
    reason: str
    evidence: list[str] = Field(default_factory=list)


class RiskVerdict(BaseModel):
    level: Level
    status: Literal["verdict", "insufficient_data"]
    vessel_class: VesselClass
    parameters: list[ParameterVerdict]
    reasons: list[str]  # worst first, only CAUTION / NO_GO parameters
    data_gaps: list[str]
    calibration: str = CALIBRATION
    computed_ms: float = 0.0

    @property
    def label(self) -> str:
        return {Level.GO: "GO", Level.CAUTION: "CAUTION", Level.NO_GO: "DO NOT SAIL"}[self.level]


def _band_verdict(
    name: str, value: float | None, unit: str, band: Band, evidence: list[str], missing_reason: str
) -> ParameterVerdict:
    if value is None:
        return ParameterVerdict(
            parameter=name,
            status="missing",
            level=None,
            unit=unit,
            caution_at=band.caution,
            no_go_at=band.no_go,
            reason=missing_reason,
        )
    lvl = band.level(value)
    cmp = "≤" if band.lower_is_worse else "≥"
    if lvl == Level.NO_GO:
        reason = f"{name} {value:g} {unit} {cmp} no-go threshold {band.no_go:g} {unit}"
    elif lvl == Level.CAUTION:
        reason = f"{name} {value:g} {unit} {cmp} caution threshold {band.caution:g} {unit}"
    else:
        reason = f"{name} {value:g} {unit} within limits"
    return ParameterVerdict(
        parameter=name,
        status="evaluated",
        level=lvl,
        value=value,
        unit=unit,
        caution_at=band.caution,
        no_go_at=band.no_go,
        reason=reason,
        evidence=evidence,
    )


def evaluate(inputs: RiskInputs, vessel: VesselClass = VesselClass.TRADITIONAL) -> RiskVerdict:
    t0 = time.perf_counter()
    th: Thresholds = TABLES[vessel]
    ev = inputs.evidence
    params: list[ParameterVerdict] = []

    # 1. Significant wave height
    params.append(
        _band_verdict(
            "wave_height",
            inputs.wave_height_m,
            "m",
            th.wave_height_m,
            ev.get("wave_height", []),
            "no wave height data",
        )
    )

    # 2. Sustained wind, with gusts as an escalator
    wind = _band_verdict(
        "wind", inputs.wind_kt, "kt", th.wind_kt, ev.get("wind", []), "no wind data"
    )
    if (
        wind.status == "evaluated"
        and inputs.gust_kt is not None
        and inputs.gust_kt >= th.wind_kt.no_go
        and wind.level < Level.CAUTION
    ):
        wind.level = Level.CAUTION
        wind.reason += f"; gusts to {inputs.gust_kt:g} kt reach the no-go threshold"
        wind.evidence = wind.evidence + ev.get("gust", [])
    params.append(wind)

    # 3. Sea steepness Hs / T²
    if inputs.wave_height_m is not None and inputs.wave_period_s:
        steep = round(inputs.wave_height_m / (inputs.wave_period_s**2), 4)
        p = _band_verdict(
            "steepness",
            steep,
            "m/s²",
            th.steepness,
            ev.get("wave_height", []) + ev.get("wave_period", []),
            "",
        )
        p.reason = p.reason.replace(
            "steepness",
            f"steepness Hs/T² ({inputs.wave_height_m:g} m / {inputs.wave_period_s:g} s²)",
        )
        params.append(p)
    else:
        params.append(
            ParameterVerdict(
                parameter="steepness",
                status="missing",
                level=None,
                unit="m/s²",
                reason="needs both wave height and period",
            )
        )

    # 4. Visibility
    params.append(
        _band_verdict(
            "visibility",
            inputs.visibility_km,
            "km",
            th.visibility_km,
            ev.get("visibility", []),
            "no visibility data",
        )
    )

    # 5. Lightning — real feed if available, otherwise a clearly-labelled convective proxy
    if inputs.lightning_data_available:
        p = _band_verdict(
            "lightning",
            inputs.lightning_km,
            "km",
            th.lightning_km,
            ev.get("lightning", []),
            "lightning feed returned nothing",
        )
        if p.level == Level.CAUTION and inputs.lightning_closing:
            p.reason += ", closing"
        params.append(p)
    else:
        proxy_level: Level | None = None
        why: list[str] = []
        if inputs.weather_code in THUNDERSTORM_CODES:
            proxy_level = Level.CAUTION
            why.append(f"forecast weather code {inputs.weather_code} (thunderstorm)")
        if inputs.cape_jkg is not None and inputs.cape_jkg >= CAPE_CAUTION_JKG:
            proxy_level = Level.CAUTION
            why.append(f"CAPE {inputs.cape_jkg:g} J/kg ≥ {CAPE_CAUTION_JKG:g}")
        if proxy_level is None:
            if inputs.weather_code is None and inputs.cape_jkg is None:
                params.append(
                    ParameterVerdict(
                        parameter="lightning",
                        status="missing",
                        level=None,
                        unit="km",
                        reason="no lightning feed (IMD key missing) and no convective proxy",
                    )
                )
            else:
                params.append(
                    ParameterVerdict(
                        parameter="lightning",
                        status="proxy",
                        level=Level.GO,
                        unit="km",
                        reason="no lightning feed; weather model shows no thunderstorm signal (proxy)",
                        evidence=ev.get("weather_code", []) + ev.get("cape", []),
                    )
                )
        else:
            params.append(
                ParameterVerdict(
                    parameter="lightning",
                    status="proxy",
                    level=proxy_level,
                    unit="km",
                    reason="no lightning feed; convective proxy: " + "; ".join(why),
                    evidence=ev.get("weather_code", []) + ev.get("cape", []),
                )
            )

    # 6. Cyclone cone
    if inputs.cyclone_data_available:
        if inputs.cyclone_hours is None:
            params.append(
                ParameterVerdict(
                    parameter="cyclone",
                    status="evaluated",
                    level=Level.GO,
                    unit="h",
                    reason="no cyclone cone intersects the area",
                    evidence=ev.get("cyclone", []),
                )
            )
        else:
            params.append(
                _band_verdict(
                    "cyclone",
                    inputs.cyclone_hours,
                    "h",
                    th.cyclone_hours,
                    ev.get("cyclone", []),
                    "",
                )
            )
    else:
        params.append(
            ParameterVerdict(
                parameter="cyclone",
                status="missing",
                level=None,
                unit="h",
                reason="no cyclone feed (IMD key missing)",
            )
        )

    # 7. Boundary — a legal hazard, but a hazard: detention is not a lesser outcome than a swamping
    if inputs.outside_indian_waters:
        params.append(
            ParameterVerdict(
                parameter="boundary",
                status="evaluated",
                level=Level.NO_GO,
                unit="min",
                reason=f"position is outside Indian waters ({inputs.boundary_name or 'IMBL'})",
                evidence=ev.get("boundary", []),
            )
        )
    elif inputs.boundary_crossing_min is not None:
        within = inputs.boundary_crossing_min <= inputs.boundary_horizon_min
        params.append(
            ParameterVerdict(
                parameter="boundary",
                status="evaluated",
                level=Level.NO_GO if within else Level.GO,
                value=inputs.boundary_crossing_min,
                unit="min",
                no_go_at=inputs.boundary_horizon_min,
                reason=(
                    f"current heading crosses {inputs.boundary_name or 'the boundary'} in {inputs.boundary_crossing_min:g} min"
                    + (
                        ""
                        if within
                        else f" (beyond the {inputs.boundary_horizon_min:g} min horizon)"
                    )
                ),
                evidence=ev.get("boundary", []),
            )
        )
    elif inputs.outside_indian_waters is False:
        params.append(
            ParameterVerdict(
                parameter="boundary",
                status="evaluated",
                level=Level.GO,
                unit="min",
                reason="inside Indian waters; no boundary on the projected track",
                evidence=ev.get("boundary", []),
            )
        )

    # -- combine: worst-of wins --------------------------------------------------------------
    levels = [p.level for p in params if p.level is not None]
    worst = max(levels, default=Level.CAUTION)
    gaps = [f"{p.parameter}: {p.reason}" for p in params if p.status == "missing"]
    critical_missing = [p for p in params if p.status == "missing" and p.parameter in CRITICAL]
    status: Literal["verdict", "insufficient_data"] = "verdict"
    if critical_missing:
        status = "insufficient_data"
        worst = max(worst, Level.CAUTION)  # never GO without wave and wind
    reasons = [
        p.reason
        for p in sorted(params, key=lambda p: -(p.level or 0))
        if p.level and p.level > Level.GO
    ]
    return RiskVerdict(
        level=worst,
        status=status,
        vessel_class=vessel,
        parameters=params,
        reasons=reasons,
        data_gaps=gaps,
        computed_ms=round((time.perf_counter() - t0) * 1000, 3),
    )
