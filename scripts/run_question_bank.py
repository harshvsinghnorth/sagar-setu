"""Run the fisherman question bank through the full system and score it.

Each question goes through exactly the path the web page uses (planner -> specialists ->
risk engine -> synthesis -> verifier). The bank records the EXPECTED UNDERSTANDING of each
question -- type, place, day, time, boat -- never a fixed answer, because the right answer
to "is it safe tomorrow" changes every day. Answers are judged on behaviour instead: a
verdict where one is needed, every number verified, the reply in the asker's language.

    uv run python scripts/run_question_bank.py               # whole bank
    uv run python scripts/run_question_bank.py --only S07 B02
    uv run python scripts/run_question_bank.py --pace 6      # seconds between questions

Writes data/question_bank/results.json and docs/question_bank_results.md. The markdown
report doubles as a recorded run for the demo if the network fails on the day.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from marine.agents.planner import detect_script  # noqa: E402
from marine.config import ROOT  # noqa: E402
from marine.graph import ask  # noqa: E402

BANK = ROOT / "data" / "question_bank" / "bank.json"
RESULTS = ROOT / "data" / "question_bank" / "results.json"
REPORT = ROOT / "docs" / "question_bank_results.md"

LLM_DOWN = "language model is unavailable"
NEEDS_VERDICT = {"safety"}
FIELDS = ("intent", "location", "day", "part", "vessel", "heading_deg", "speed_kt")


def _val(x):
    return getattr(x, "value", x)


def _matches(field: str, expected, actual) -> bool:
    if field == "location":
        name = (actual or "").lower()
        return bool(name) and any(e in name for e in expected)
    if field == "heading_deg":
        return actual is not None and abs(float(actual) - float(expected)) <= 15
    if field == "speed_kt":
        return actual is not None and abs(float(actual) - float(expected)) <= 0.5
    if isinstance(expected, list):
        return actual in expected
    return actual == expected


async def run_one(item: dict, retries: int, backoff: float) -> dict:
    """Ask one question; retry if the model was rate-limited rather than score it as a miss."""
    attempt = 0
    while True:
        t0 = time.perf_counter()
        try:
            state = await ask(item["q"], llm="auto")
        except Exception as e:  # a crash is a result, not a reason to stop the run
            return {"id": item["id"], "error": f"{type(e).__name__}: {e}"}
        plan = state["plan"]
        if (
            _val(plan.intent) == "clarify"
            and LLM_DOWN in (plan.clarify_question or "")
            and attempt < retries
        ):
            attempt += 1
            print(f"    model unavailable, retry {attempt}/{retries} in {backoff:.0f}s")
            await asyncio.sleep(backoff * attempt)
            continue
        break

    ans = state.get("answer")
    total_ms = next((e["ms"] for e in reversed(state.get("events", [])) if e["node"] == "total"),
                    round((time.perf_counter() - t0) * 1000))
    got = {
        "language": plan.language,
        "intent": _val(plan.intent),
        "location": plan.location.name if plan.location else None,
        "day": plan.day,
        "part": plan.part,
        "vessel": _val(plan.vessel) if plan.vessel else None,
        "heading_deg": plan.heading_deg,
        "speed_kt": plan.speed_kt,
        "planner": plan.source,
    }
    exp = item["expect"]
    field_ok = {f: _matches(f, exp[f], got[f]) for f in FIELDS if f in exp}
    lang_ok = got["language"] == item["lang"]
    understood = all(field_ok.values()) and lang_ok

    text = ans.text if ans else ""
    verdict = ans.verdict if ans else None
    verified = bool(ans and ans.verification.ok)
    answer_script = detect_script(text) if text else None
    # A Hindi question typed in English letters may fairly be answered in either script.
    script_ok = answer_script == item["lang"] or (item.get("style") == "code-mixed" and answer_script == "en")
    behaviour = {
        "answered": bool(text.strip()),
        "numbers_verified": verified,
        "reply_language": script_ok,
    }
    if got["intent"] in NEEDS_VERDICT and exp.get("intent") in ("safety", ["safety", "boundary"]):
        behaviour["verdict_given"] = verdict is not None
    if item["category"] in ("off_topic", "general_knowledge", "clarify"):
        behaviour["no_verdict"] = verdict is None
    llm_down = LLM_DOWN in (plan.clarify_question or "")

    return {
        "id": item["id"],
        "category": item["category"],
        "lang": item["lang"],
        "style": item.get("style", "plain"),
        "q": item["q"],
        "en": item.get("en"),
        "expect": exp,
        "got": got,
        "field_ok": field_ok,
        "language_ok": lang_ok,
        "understood": understood,
        "behaviour": behaviour,
        "behaved": all(behaviour.values()),
        "verdict": verdict,
        "answer": text,
        "answer_source": ans.source if ans else None,
        "unsupported_numbers": ans.verification.unsupported if ans else [],
        "degradation": list(ans.degradation) if ans else [],
        "llm_unavailable": llm_down,
        "ms": total_ms,
    }


def _pct(n: int, d: int) -> str:
    return f"{n}/{d} ({(100 * n / d):.0f} %)" if d else "—"


def summarise(rows: list[dict]) -> dict:
    ok = [r for r in rows if "error" not in r and not r["llm_unavailable"]]
    by = lambda key: {  # noqa: E731
        k: _pct(sum(r["understood"] for r in g), len(g))
        for k, g in sorted(_group(ok, key).items())
    }
    field = {}
    for f in ("language",) + FIELDS:
        if f == "language":
            field[f] = _pct(sum(r["language_ok"] for r in ok), len(ok))
            continue
        scored = [r for r in ok if f in r["field_ok"]]
        field[f] = _pct(sum(r["field_ok"][f] for r in scored), len(scored))
    beh = defaultdict(lambda: [0, 0])
    for r in ok:
        for k, v in r["behaviour"].items():
            beh[k][0] += v
            beh[k][1] += 1
    return {
        "run_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "questions": len(rows),
        "scored": len(ok),
        "errors": [r["id"] for r in rows if "error" in r],
        "llm_unavailable": [r["id"] for r in rows if r.get("llm_unavailable")],
        "understood": _pct(sum(r["understood"] for r in ok), len(ok)),
        "behaved": _pct(sum(r["behaved"] for r in ok), len(ok)),
        "by_language": by("lang"),
        "by_category": by("category"),
        "by_style": by("style"),
        "fields": field,
        "behaviour": {k: _pct(*v) for k, v in beh.items()},
        "answer_sources": dict(sorted(_count(r["answer_source"] for r in ok).items())),
        "median_ms": round(statistics.median(r["ms"] for r in ok)) if ok else None,
    }


def _group(rows, key):
    g = defaultdict(list)
    for r in rows:
        g[r[key]].append(r)
    return g


def _count(xs):
    c = defaultdict(int)
    for x in xs:
        c[str(x)] += 1
    return c


LANG = {"en": "English", "ta": "Tamil", "hi": "Hindi", "ml": "Malayalam"}


def report(summary: dict, rows: list[dict], categories: dict) -> str:
    L = ["# Sagar Setu — question bank results", ""]
    L.append(f"*Run {summary['run_at']} · {summary['questions']} questions · generated by "
             "`scripts/run_question_bank.py` from `data/question_bank/bank.json`.*")
    L.append("")
    L.append("Each question is scored on whether the system **understood** it — the right type, "
             "place, day, time, boat and language — and on whether the **answer behaved** "
             "correctly: a verdict where one was needed, every number verified against the "
             "evidence ledger, the reply in the asker's language. Answers themselves are not "
             "compared with fixed text: the right answer to *is it safe tomorrow* changes daily.")
    L.append("")
    L.append("## Summary")
    L.append("")
    L.append("| | |")
    L.append("|---|---|")
    L.append(f"| **Understood correctly** | **{summary['understood']}** |")
    L.append(f"| **Answer behaved correctly** | **{summary['behaved']}** |")
    L.append(f"| Median time per question | {summary['median_ms'] / 1000:.1f} s |" if summary["median_ms"] else "| Median time | — |")
    if summary["errors"]:
        L.append(f"| Crashed | {', '.join(summary['errors'])} |")
    if summary["llm_unavailable"]:
        L.append(f"| Not scored (model rate-limited) | {', '.join(summary['llm_unavailable'])} |")
    L.append("")
    for title, key, names in (("By language", "by_language", LANG),
                              ("By question type", "by_category", categories),
                              ("By phrasing", "by_style", {})):
        L.append(f"### {title}")
        L.append("")
        L.append("| | Understood |")
        L.append("|---|---|")
        for k, v in summary[key].items():
            L.append(f"| {names.get(k, k)} | {v} |")
        L.append("")
    L.append("### Field by field")
    L.append("")
    L.append("| Field | Correct |")
    L.append("|---|---|")
    for k, v in summary["fields"].items():
        L.append(f"| {k} | {v} |")
    L.append("")
    L.append("### Answer behaviour")
    L.append("")
    L.append("| Check | Passed |")
    L.append("|---|---|")
    for k, v in summary["behaviour"].items():
        L.append(f"| {k.replace('_', ' ')} | {v} |")
    L.append("")
    L.append(f"Answer written by: {', '.join(f'{k} × {v}' for k, v in summary['answer_sources'].items())}. "
             "`llm` = model's first draft passed the verifier; `llm_retry` = first draft rejected, "
             "second passed; `template_fallback` = both rejected, fixed template used; `clarify` = "
             "the system asked a follow-up question.")
    L.append("")
    L.append("## Every question")
    L.append("")
    for r in rows:
        if "error" in r:
            L.append(f"### {r['id']} — ERROR")
            L.append("")
            L.append(f"`{r['error']}`")
            L.append("")
            continue
        mark = "✅" if r["understood"] and r["behaved"] else ("⚠️" if r["understood"] else "❌")
        L.append(f"### {mark} {r['id']} · {categories.get(r['category'], r['category'])} · "
                 f"{LANG.get(r['lang'], r['lang'])} · {r['style']}")
        L.append("")
        L.append(f"> **{r['q']}**")
        if r.get("en"):
            L.append(f">  \n> *{r['en']}*")
        L.append("")
        g = r["got"]
        wrong = [f for f, ok in r["field_ok"].items() if not ok] + ([] if r["language_ok"] else ["language"])
        L.append(f"Understood as: **{g['intent']}** · {g['location'] or 'no place'} · {g['day']} {g['part']}"
                 + (f" · {g['vessel']}" if g["vessel"] else "")
                 + (f" · heading {g['heading_deg']:g}°" if g["heading_deg"] is not None else "")
                 + (f" · {g['speed_kt']:g} kt" if g["speed_kt"] is not None else "")
                 + f" · lang {g['language']} · via {g['planner']}")
        if wrong:
            L.append(f"  \n**Mismatched:** {', '.join(wrong)} (expected "
                     + "; ".join(f"{f}={r['expect'].get(f, r['lang'] if f == 'language' else '?')}" for f in wrong) + ")")
        bad_beh = [k for k, v in r["behaviour"].items() if not v]
        if bad_beh:
            L.append(f"  \n**Behaviour issue:** {', '.join(bad_beh)}")
        L.append("")
        if r["verdict"]:
            L.append(f"**Verdict: {r['verdict']}** · answer via `{r['answer_source']}` · {r['ms'] / 1000:.1f} s")
        else:
            L.append(f"Answer via `{r['answer_source']}` · {r['ms'] / 1000:.1f} s")
        L.append("")
        for line in (r["answer"] or "(no answer)").strip().splitlines():
            L.append(f"> {line}" if line.strip() else ">")
        if r["unsupported_numbers"]:
            L.append("")
            L.append(f"Unsupported numbers caught: {', '.join(r['unsupported_numbers'])}")
        L.append("")
    return "\n".join(L)


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="question ids to run")
    ap.add_argument("--pace", type=float, default=4.0, help="seconds between questions")
    ap.add_argument("--retries", type=int, default=3)
    ap.add_argument("--backoff", type=float, default=20.0)
    args = ap.parse_args()

    bank = json.loads(BANK.read_text(encoding="utf-8"))
    items = [q for q in bank["questions"] if not args.only or q["id"] in args.only]
    rows: list[dict] = []
    for i, item in enumerate(items, 1):
        print(f"[{i:>2}/{len(items)}] {item['id']} {item['q']}")
        r = await run_one(item, args.retries, args.backoff)
        rows.append(r)
        if "error" in r:
            print(f"    ERROR {r['error']}")
        else:
            flag = "OK " if r["understood"] and r["behaved"] else ("BEH" if r["understood"] else "MISS")
            print(f"    {flag} {r['got']['intent']:<17} {str(r['got']['location']):<16} "
                  f"verdict={r['verdict']} via={r['answer_source']} {r['ms'] / 1000:.1f}s")
        if i < len(items):
            await asyncio.sleep(args.pace)

    if args.only and RESULTS.exists():  # merge a partial re-run into the full results
        prev = {r["id"]: r for r in json.loads(RESULTS.read_text(encoding="utf-8"))["rows"]}
        prev.update({r["id"]: r for r in rows})
        order = [q["id"] for q in bank["questions"]]
        rows = [prev[i] for i in order if i in prev]

    summary = summarise(rows)
    RESULTS.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2),
                       encoding="utf-8")
    REPORT.write_text(report(summary, rows, bank["categories"]), encoding="utf-8")
    print()
    print(f"understood: {summary['understood']}   behaved: {summary['behaved']}   "
          f"median {summary['median_ms']} ms")
    print(f"wrote {RESULTS.relative_to(ROOT)} and {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    asyncio.run(main())
