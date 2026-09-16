"""Phase 3 exit criterion: a question in any language → planner → specialists → risk engine →
verified answer in the same language, with the ledger and timings.

  uv run python scripts/chat.py "Is it safe to go out from Kochi tomorrow morning?"
  uv run python scripts/chat.py "நாளை காலை கொச்சியில் இருந்து கடலுக்கு போகலாமா?"
  uv run python scripts/chat.py --llm none "where are the fish near paradip"   # deterministic only
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from marine.graph import ask  # noqa: E402


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--llm", default="auto", help="auto | gemini | anthropic | ollama | none")
    ap.add_argument("--ledger", action="store_true")
    a = ap.parse_args()

    printed = False

    async def on_chunk(ch: str) -> None:
        nonlocal printed
        if not printed:
            print("\n--- answer ---")
            printed = True
        print(ch, end="", flush=True)

    out = await ask(a.query, llm=a.llm, on_chunk=on_chunk)
    if not printed:
        print("\n--- answer ---\n" + out["answer"].text)
    print("\n--- trace ---")
    for e in out["events"]:
        print(f"  {e['node']:<14} {e['status']:<7} {e['ms']:>6} ms  {e['detail']}")
    ans, plan = out["answer"], out["plan"]
    print(
        f"\nplan: {plan.source} intent={plan.intent} lang={plan.language} "
        + (
            f"loc={plan.location.name} {plan.day}/{plan.part} vessel={plan.vessel}"
            if plan.location
            else ""
        )
    )
    print(
        f"answer: source={ans.source} verified={ans.verification.ok} numbers={ans.verification.numbers_found}"
        + (f" UNSUPPORTED={ans.verification.unsupported}" if ans.verification.unsupported else "")
    )
    led = out["ctx"].ledger
    print(
        f"ledger: {len(led.observations)} observations, {len(led.missing)} missing, degraded={led.degraded()}"
    )
    if a.ledger:
        for o in led.observations:
            print(
                f"  {o.id} {o.variable:<24} {o.value:>8g} {o.unit:<6} {o.source:<28} {o.provenance}"
            )


if __name__ == "__main__":
    asyncio.run(main())
