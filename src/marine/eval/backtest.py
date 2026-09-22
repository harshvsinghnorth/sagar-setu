"""Backtest: how often would the verdict issued the day before have matched what the morning
actually brought?

Truth here is the wave/weather model's own final analysis for each hour (Open-Meteo, lead
0–23 h); the prediction is the forecast for the same hour issued 1, 2 or 3 days earlier
(`*_previous_dayN`). So this measures forecast-plus-threshold skill against the model's
best estimate of what happened — NOT against buoys. It is stated as such everywhere.

For every harbour and every day in the window we build the morning (05:00–12:00 IST)
worst-of inputs from both series, run the same deterministic engine on each, and compare.
Verification metrics follow the standard 2×2 contingency table used for warnings:

    hit rate (POD)         = hits / (hits + misses)          — how often a rough morning was warned
    false alarm ratio (FAR)= false alarms / (hits + false alarms) — how often a warning wasted a day
    critical success index = hits / (hits + misses + false alarms)
    accuracy               = (hits + correct negatives) / all
"""

from __future__ import annotations

import asyncio
import json
import statistics
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

import httpx

from marine.config import DATA_DIR
from marine.fixtures import HARBOURS
from marine.risk.rules import RiskInputs, evaluate
from marine.risk.thresholds import Level, VesselClass

EVAL_DIR = DATA_DIR / "eval"
LEADS = (1, 2, 3)
# Morning window 05:00–12:00 IST = 23:30 UTC (previous day) → 06:30 UTC. Hourly data: 00–06 UTC.
WINDOW_UTC_HOURS = range(0, 7)


@dataclass
class DayCase:
    harbour: str
    day: date
    lead: int
    truth: RiskInputs
    forecast: RiskInputs
    truth_level: Level
    forecast_level: Level
    hs_truth: float
    hs_forecast: float


@dataclass
class Contingency:
    hits: int = 0
    misses: int = 0
    false_alarms: int = 0
    correct_negatives: int = 0

    @property
    def n(self) -> int:
        return self.hits + self.misses + self.false_alarms + self.correct_negatives

    def metrics(self) -> dict:
        def div(a, b):
            return round(a / b, 3) if b else None

        return {
            "n": self.n,
            "hits": self.hits,
            "misses": self.misses,
            "false_alarms": self.false_alarms,
            "correct_negatives": self.correct_negatives,
            "hit_rate_pod": div(self.hits, self.hits + self.misses),
            "false_alarm_ratio": div(self.false_alarms, self.hits + self.false_alarms),
            "critical_success_index": div(self.hits, self.hits + self.misses + self.false_alarms),
            "accuracy": div(self.hits + self.correct_negatives, self.n),
            "event_base_rate": div(self.hits + self.misses, self.n),
        }


@dataclass
class Metrics:
    cases: int = 0
    three_class_agreement: float | None = None
    no_go: Contingency = field(default_factory=Contingency)  # event = DO NOT SAIL
    not_go: Contingency = field(default_factory=Contingency)  # event = CAUTION or worse
    hs_mae: float | None = None
    hs_rmse: float | None = None
    hs_bias: float | None = None
    confusion: dict[str, dict[str, int]] = field(default_factory=dict)


async def fetch_history(lat: float, lon: float, past_days: int = 92) -> tuple[dict, dict]:
    leads = ",".join(f"{v}_previous_day{n}" for v in ("wave_height", "wave_period") for n in LEADS)
    wleads = ",".join(
        f"{v}_previous_day{n}" for v in ("wind_speed_10m", "wind_gusts_10m") for n in LEADS
    )
    async with httpx.AsyncClient(timeout=90) as c:
        m, w = await asyncio.gather(
            c.get(
                "https://marine-api.open-meteo.com/v1/marine",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "hourly": f"wave_height,wave_period,{leads}",
                    "past_days": past_days,
                    "forecast_days": 1,
                    "timezone": "UTC",
                },
            ),
            c.get(
                "https://previous-runs-api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "hourly": f"wind_speed_10m,wind_gusts_10m,{wleads}",
                    "past_days": past_days,
                    "forecast_days": 1,
                    "wind_speed_unit": "kn",
                    "timezone": "UTC",
                },
            ),
        )
    m.raise_for_status()
    w.raise_for_status()
    return m.json()["hourly"], w.json()["hourly"]


def _by_day(hourly: dict, key: str) -> dict[date, list[float]]:
    out: dict[date, list[float]] = {}
    for t, v in zip(hourly["time"], hourly[key], strict=False):
        dt = datetime.fromisoformat(t)
        if dt.hour in WINDOW_UTC_HOURS and v is not None:
            out.setdefault(dt.date(), []).append(float(v))
    return out


def _inputs(hs: list[float], per: list[float], wind: list[float], gust: list[float]) -> RiskInputs:
    i_max = max(range(len(hs)), key=lambda i: hs[i])
    return RiskInputs(
        wave_height_m=hs[i_max],
        wave_period_s=per[i_max] if i_max < len(per) else None,
        wind_kt=max(wind),
        gust_kt=max(gust) if gust else None,
        visibility_km=10.0,  # not archived with previous runs; held neutral for both series
    )


def build_cases(harbour: str, marine: dict, weather: dict) -> list[DayCase]:
    cases: list[DayCase] = []
    t_hs, t_per = _by_day(marine, "wave_height"), _by_day(marine, "wave_period")
    t_wind, t_gust = _by_day(weather, "wind_speed_10m"), _by_day(weather, "wind_gusts_10m")
    today = datetime.now(UTC).date()
    for lead in LEADS:
        f_hs, f_per = (
            _by_day(marine, f"wave_height_previous_day{lead}"),
            _by_day(marine, f"wave_period_previous_day{lead}"),
        )
        f_wind, f_gust = (
            _by_day(weather, f"wind_speed_10m_previous_day{lead}"),
            _by_day(weather, f"wind_gusts_10m_previous_day{lead}"),
        )
        for d in sorted(t_hs):
            if d >= today or any(d not in x for x in (t_per, t_wind, f_hs, f_per, f_wind)):
                continue
            if len(t_hs[d]) < 5 or len(f_hs[d]) < 5:
                continue
            ti = _inputs(t_hs[d], t_per[d], t_wind[d], t_gust.get(d, []))
            fi = _inputs(f_hs[d], f_per[d], f_wind[d], f_gust.get(d, []))
            tv, fv = evaluate(ti, VesselClass.TRADITIONAL), evaluate(fi, VesselClass.TRADITIONAL)
            cases.append(
                DayCase(
                    harbour, d, lead, ti, fi, tv.level, fv.level, ti.wave_height_m, fi.wave_height_m
                )
            )
    return cases


def score(cases: list[DayCase]) -> Metrics:
    m = Metrics(cases=len(cases))
    if not cases:
        return m
    names = {Level.GO: "GO", Level.CAUTION: "CAUTION", Level.NO_GO: "NO_GO"}
    conf = {a: {b: 0 for b in names.values()} for a in names.values()}
    errs = []
    for c in cases:
        conf[names[c.truth_level]][names[c.forecast_level]] += 1
        errs.append(c.hs_forecast - c.hs_truth)
        for cont, thr in ((m.no_go, Level.NO_GO), (m.not_go, Level.CAUTION)):
            event, warned = c.truth_level >= thr, c.forecast_level >= thr
            if event and warned:
                cont.hits += 1
            elif event:
                cont.misses += 1
            elif warned:
                cont.false_alarms += 1
            else:
                cont.correct_negatives += 1
    m.confusion = conf
    m.three_class_agreement = round(
        sum(1 for c in cases if c.truth_level == c.forecast_level) / len(cases), 3
    )
    m.hs_mae = round(statistics.fmean(abs(e) for e in errs), 3)
    m.hs_rmse = round((statistics.fmean(e * e for e in errs)) ** 0.5, 3)
    m.hs_bias = round(statistics.fmean(errs), 3)
    return m


def metrics_dict(m: Metrics) -> dict:
    return {
        "cases": m.cases,
        "three_class_agreement": m.three_class_agreement,
        "no_go_event": m.no_go.metrics(),
        "caution_or_worse_event": m.not_go.metrics(),
        "hs_mae_m": m.hs_mae,
        "hs_rmse_m": m.hs_rmse,
        "hs_bias_m": m.hs_bias,
        "confusion_truth_rows_forecast_cols": m.confusion,
    }


async def run(past_days: int = 92, harbours: dict[str, tuple[float, float]] | None = None) -> dict:
    harbours = harbours or HARBOURS
    all_cases: list[DayCase] = []
    per_harbour: dict[str, dict] = {}
    for name, (lat, lon) in harbours.items():
        marine, weather = await fetch_history(lat, lon, past_days)
        cases = build_cases(name, marine, weather)
        all_cases += cases
        per_harbour[name] = {
            f"lead_{n}": metrics_dict(score([c for c in cases if c.lead == n])) for n in LEADS
        }
        per_harbour[name]["days"] = len({c.day for c in cases})
    pooled = {
        f"lead_{n}": metrics_dict(score([c for c in all_cases if c.lead == n])) for n in LEADS
    }
    days = sorted({c.day for c in all_cases})
    out = {
        "generated_at": datetime.now(UTC).isoformat(),
        "truth": "Open-Meteo model final analysis for each hour (lead 0–23 h); NOT buoy observations",
        "prediction": "the same model's forecast for the same hour issued N days earlier (previous_dayN)",
        "window": "05:00–12:00 IST (00–06 UTC), worst-of per parameter",
        "vessel_class": "traditional (< 12 m)",
        "parameters": "wave height, wave period (steepness), wind, gusts; visibility held neutral; lightning/cyclone absent in both",
        "period": {
            "from": days[0].isoformat() if days else None,
            "to": days[-1].isoformat() if days else None,
            "days": len(days),
        },
        "pooled": pooled,
        "per_harbour": per_harbour,
    }
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    (EVAL_DIR / "backtest.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out
