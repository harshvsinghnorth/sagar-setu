"""Prospective verification: record tomorrow-morning verdicts today, check them tomorrow.

  uv run python scripts/daily_log.py --log      # evening: verdict for tomorrow morning, 5 harbours
  uv run python scripts/daily_log.py --verify   # next afternoon: what the morning actually brought

Appends to data/eval/verdict_log.jsonl. Unlike the backtest, these are predictions made
before the fact — the strongest evidence a reviewer can be given. `scripts/eval_report.py`
folds verified days into docs/evaluation.md.

To automate on Windows (once, in PowerShell), two scheduled tasks:
  schtasks /Create /SC DAILY /ST 18:00 /TN SagarSetuLog    /TR "cmd /c cd /d <repo> && uv run python scripts/daily_log.py --log"
  schtasks /Create /SC DAILY /ST 14:00 /TN SagarSetuVerify /TR "cmd /c cd /d <repo> && uv run python scripts/daily_log.py --verify"
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from marine.eval.backtest import EVAL_DIR  # noqa: E402
from marine.fixtures import HARBOURS  # noqa: E402
from marine.risk.thresholds import VesselClass  # noqa: E402
from marine.tools import RiskQuery, ToolContext, named_window, safety_briefing  # noqa: E402

LOG = EVAL_DIR / "verdict_log.jsonl"


def _rows() -> list[dict]:
    if not LOG.exists():
        return []
    return [json.loads(x) for x in LOG.read_text(encoding="utf-8").splitlines() if x.strip()]


def _write(rows: list[dict]) -> None:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    LOG.write_text("".join(json.dumps(r, default=str) + "\n" for r in rows), encoding="utf-8")


def _values(v) -> dict:
    return {p.parameter: p.value for p in v.parameters if p.value is not None}


async def log() -> None:
    rows = _rows()
    start, end = named_window("tomorrow", "morning")
    done = {(r["harbour"], r["window_start"]) for r in rows}
    for name, (lat, lon) in HARBOURS.items():
        if (name, start.isoformat()) in done:
            continue
        ctx = ToolContext()
        b = await safety_briefing(
            ctx, RiskQuery(lat=lat, lon=lon, start=start, end=end, vessel=VesselClass.TRADITIONAL)
        )
        v = b.verdict
        rows.append(
            {
                "harbour": name,
                "lat": lat,
                "lon": lon,
                "logged_at": datetime.now(UTC).isoformat(),
                "window_start": start.isoformat(),
                "window_end": end.isoformat(),
                "forecast_level": int(v.level),
                "forecast_label": v.label,
                "forecast_status": v.status,
                "forecast_values": _values(v),
                "forecast_reasons": v.reasons,
                "sources": ctx.ledger.sources(),
                "observed_level": None,
            }
        )
        print(f"  logged {name:<11} {v.label:<12} {v.reasons[:1]}")
    _write(rows)


async def verify() -> None:
    rows = _rows()
    now = datetime.now(UTC)
    n = 0
    for r in rows:
        end = datetime.fromisoformat(r["window_end"])
        if r["observed_level"] is not None or end > now:
            continue
        start = datetime.fromisoformat(r["window_start"])
        ctx = ToolContext()
        b = await safety_briefing(
            ctx,
            RiskQuery(
                lat=r["lat"], lon=r["lon"], start=start, end=end, vessel=VesselClass.TRADITIONAL
            ),
        )
        v = b.verdict
        r.update(
            {
                "verified_at": now.isoformat(),
                "observed_level": int(v.level),
                "observed_label": v.label,
                "observed_status": v.status,
                "observed_values": _values(v),
                "observed_reasons": v.reasons,
                "observed_sources": ctx.ledger.sources(),
            }
        )
        n += 1
        mark = "ok" if v.level == r["forecast_level"] else "DIFF"
        print(
            f"  {r['harbour']:<11} {r['window_start'][:10]} forecast {r['forecast_label']:<12} observed {v.label:<12} {mark}"
        )
    _write(rows)
    print(
        f"verified {n} entries; {sum(1 for r in rows if r['observed_level'] is not None)} verified in total"
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", action="store_true")
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    if a.log:
        asyncio.run(log())
    if a.verify:
        asyncio.run(verify())
    if not (a.log or a.verify):
        ap.print_help()
