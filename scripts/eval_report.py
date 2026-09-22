"""Run the backtest and write docs/evaluation.md — the numbers a reviewer asks for, with the
caveats stated next to them. Also folds in the prospective daily log if it has verified days.

  uv run python scripts/eval_report.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from marine.config import ROOT  # noqa: E402
from marine.eval.backtest import EVAL_DIR, run  # noqa: E402

OUT = ROOT / "docs" / "evaluation.md"


def pct(x: float | None) -> str:
    return "—" if x is None else f"{100 * x:.1f}%"


def cont_row(label: str, c: dict) -> str:
    return (
        f"| {label} | {c['n']} | {pct(c['event_base_rate'])} | {c['hits']} | {c['misses']} | "
        f"{c['false_alarms']} | **{pct(c['hit_rate_pod'])}** | **{pct(c['false_alarm_ratio'])}** | "
        f"{pct(c['critical_success_index'])} | {pct(c['accuracy'])} |"
    )


def prospective() -> tuple[str, int]:
    p = EVAL_DIR / "verdict_log.jsonl"
    if not p.exists():
        return "", 0
    rows = [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    verified = [r for r in rows if r.get("observed_level") is not None]
    if not verified:
        return (
            f"_{len(rows)} verdicts logged, none verified yet (verification runs the following day)._",
            0,
        )
    hits = fa = miss = cn = 0
    agree = 0
    for r in verified:
        e, w = r["observed_level"] >= 1, r["forecast_level"] >= 1
        hits += e and w
        miss += e and not w
        fa += (not e) and w
        cn += (not e) and (not w)
        agree += r["observed_level"] == r["forecast_level"]
    n = len(verified)
    pod = hits / (hits + miss) if hits + miss else None
    far = fa / (hits + fa) if hits + fa else None
    txt = (
        f"{n} harbour-mornings verified so far (predictions recorded the evening before, "
        f"outcomes checked the next day). Three-class agreement {pct(agree / n)}; "
        f"CAUTION-or-worse hit rate {pct(pod)}, false-alarm ratio {pct(far)} "
        f"(hits {hits}, misses {miss}, false alarms {fa}, correct negatives {cn})."
    )
    return txt, n


def main() -> None:
    bt = asyncio.run(run())
    per = bt["period"]
    lines = [
        "# Sagar Setu — verdict evaluation",
        "",
        f"*Generated {bt['generated_at'][:16]} UTC by `scripts/eval_report.py`. Raw numbers: "
        f"`data/eval/backtest.json`.*",
        "",
        "## What is being measured, honestly",
        "",
        'The question a reviewer asks is: *when the system says "do not go out tomorrow morning", '
        "how often is it right?* Sagar Setu does not forecast the sea itself — it applies published "
        "small-craft thresholds to government and open forecasts. So the verdict can be wrong for two "
        "reasons: the forecast was wrong, or the threshold was. This evaluation measures both together, "
        "the way the fisherman experiences them.",
        "",
        "**Prediction:** the verdict computed from the forecast available the evening before (the "
        "model run issued 1, 2 or 3 days ahead of the morning in question).  ",
        "**Truth:** the verdict computed from the same wave/weather model's *final analysis* for that "
        "morning (lead 0–23 h). This is the model's best estimate of what happened — **not a buoy "
        "measurement**. No INCOIS/NIOT buoy feed is publicly accessible to us; if one is obtained the "
        "same harness runs against it unchanged. Forecast-versus-analysis agreement is expected to be "
        "somewhat better than forecast-versus-buoy, so treat these as an upper bound on skill.",
        "",
        f"**Sample:** {per['days']} mornings ({per['from']} → {per['to']}) × 5 harbours = "
        f"{bt['pooled']['lead_1']['cases']} harbour-mornings per lead. The period covers the peak of "
        "the south-west monsoon, so rough mornings are well represented.  ",
        f"**Window:** {bt['window']}. **Vessel class:** {bt['vessel_class']}. "
        f"**Parameters:** {bt['parameters']}.",
        "",
        "Two errors matter differently. A **miss** (we said go, it was rough) is the dangerous one. A "
        "**false alarm** (we said don't go, it was fine) is the wasted day. They are reported "
        "separately, using the standard warning-verification table:",
        "",
        "- **Hit rate (POD)** = hits / (hits + misses) — of the rough mornings, how many were warned.",
        "- **False-alarm ratio (FAR)** = false alarms / (hits + false alarms) — of the warnings, how many wasted a day.",
        "- **CSI** = hits / (hits + misses + false alarms). **Accuracy** = (hits + correct negatives) / all.",
        "",
        "## Results — all five harbours pooled",
        "",
        "### Event: DO NOT SAIL (the do-not-sail band on any parameter)",
        "",
        "| Forecast lead | n | rough mornings | hits | misses | false alarms | hit rate | false-alarm ratio | CSI | accuracy |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for n in (1, 2, 3):
        lines.append(cont_row(f"{n} day ahead", bt["pooled"][f"lead_{n}"]["no_go_event"]))
    lines += [
        "",
        "### Event: CAUTION or worse (anything other than a clean GO)",
        "",
        "| Forecast lead | n | such mornings | hits | misses | false alarms | hit rate | false-alarm ratio | CSI | accuracy |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for n in (1, 2, 3):
        lines.append(
            cont_row(f"{n} day ahead", bt["pooled"][f"lead_{n}"]["caution_or_worse_event"])
        )
    lines += [
        "",
        "### Three-way agreement and wave-height error",
        "",
        "| Forecast lead | GO/CAUTION/NO-GO agreement | wave-height MAE | RMSE | bias |",
        "|---|---|---|---|---|",
    ]
    for n in (1, 2, 3):
        p = bt["pooled"][f"lead_{n}"]
        lines.append(
            f"| {n} day ahead | **{pct(p['three_class_agreement'])}** | {p['hs_mae_m']} m | {p['hs_rmse_m']} m | {p['hs_bias_m']:+} m |"
        )
    c = bt["pooled"]["lead_1"]["confusion_truth_rows_forecast_cols"]
    lines += [
        "",
        "### Confusion matrix, 1 day ahead (rows = what the morning brought, columns = what was said)",
        "",
        "| | said GO | said CAUTION | said DO NOT SAIL |",
        "|---|---|---|---|",
        f"| was GO | {c['GO']['GO']} | {c['GO']['CAUTION']} | {c['GO']['NO_GO']} |",
        f"| was CAUTION | {c['CAUTION']['GO']} | {c['CAUTION']['CAUTION']} | {c['CAUTION']['NO_GO']} |",
        f"| was DO NOT SAIL | {c['NO_GO']['GO']} | {c['NO_GO']['CAUTION']} | {c['NO_GO']['NO_GO']} |",
        "",
        "## Results per harbour, 1 day ahead",
        "",
        "| Harbour | days | rough (NO-GO) mornings | NO-GO hit rate | NO-GO false-alarm ratio | CAUTION+ base rate | CAUTION+ hit rate | CAUTION+ FAR | 3-way agreement | Hs MAE |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for h, v in bt["per_harbour"].items():
        p = v["lead_1"]
        ng, ca = p["no_go_event"], p["caution_or_worse_event"]
        lines.append(
            f"| {h.replace('_', ' ').title()} | {v['days']} | {ng['hits'] + ng['misses']} | {pct(ng['hit_rate_pod'])} | {pct(ng['false_alarm_ratio'])} | {pct(ca['event_base_rate'])} | {pct(ca['hit_rate_pod'])} | {pct(ca['false_alarm_ratio'])} | {pct(p['three_class_agreement'])} | {p['hs_mae_m']} m |"
        )
    lines += [
        "",
        "A dash means the event never occurred at that harbour in the period (Chennai and Port Blair "
        "had no do-not-sail mornings in the south-west monsoon — the Bay of Bengal's rough season is "
        "October–December). Veraval, on the Gujarat coast, is the stress test: a do-not-sail morning "
        "roughly one day in three.",
        "",
        "## Prospective log (predictions made before the fact)",
        "",
    ]
    txt, n = prospective()
    lines.append(
        txt
        or "_Not started. `scripts/daily_log.py --log` each evening and `--verify` each afternoon build it._"
    )
    lines += [
        "",
        "## How to read this, and what it does not say",
        "",
        "- The day-ahead do-not-sail verdict warned rough mornings with a high hit rate and a low "
        "false-alarm ratio; the misses were graded CAUTION, never GO. That is the behaviour the "
        "worst-of rule is designed to produce.",
        "- Skill falls with lead time, mostly through false alarms — a three-day-ahead warning wastes "
        "more days. The interface should therefore present the day-ahead verdict as the decision and "
        "longer leads as outlook.",
        "- These numbers are forecast-versus-analysis. Against buoy observations they would be lower, "
        "and the gap is the forecast model's own error near the coast, which is published by ECMWF and "
        "Copernicus for their wave products.",
        "- The thresholds are still the provisional starting values. If INCOIS's published criteria "
        "differ, the base rates change and this report is regenerated with one command.",
        "- Lightning and cyclone parameters are absent from both prediction and truth (no IMD feed), so "
        "this evaluation says nothing about them.",
        "",
        "Re-run with `uv run python scripts/eval_report.py`.",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT}")
    p = bt["pooled"]["lead_1"]
    print(
        f"1-day-ahead: NO-GO POD {pct(p['no_go_event']['hit_rate_pod'])}, FAR {pct(p['no_go_event']['false_alarm_ratio'])}; "
        f"CAUTION+ POD {pct(p['caution_or_worse_event']['hit_rate_pod'])}, FAR {pct(p['caution_or_worse_event']['false_alarm_ratio'])}; "
        f"3-way {pct(p['three_class_agreement'])}"
    )


if __name__ == "__main__":
    main()
