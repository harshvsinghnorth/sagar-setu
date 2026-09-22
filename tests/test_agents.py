"""Phase 3 smoke tests: planner fast path, DAG shape, verifier, and the graph end to end.
No network (snapshot fixtures from test_tools) and no real model — a scripted fake LLM
stands in, including one that hallucinates a number so the verifier has to catch it.
Agent behaviour gets smoke tests, not assertions on exact wording (CLAUDE.md)."""

from __future__ import annotations

import json
from datetime import UTC, datetime

import httpx
import pytest

from marine.agents.llm import LLMUnavailable
from marine.agents.planner import Intent, fast_plan, make_plan, tasks_for
from marine.agents.synthesis import Brief, template_answer, verify
from marine.config import SNAPSHOT_DIR
from marine.graph import ask
from marine.sources import base
from marine.tools import ToolContext

# -- fixtures: network stub (same as test_tools) ------------------------------------------------


@pytest.fixture
def live_from_snapshot(monkeypatch, tmp_path):
    def handler(request):
        host = request.url.host
        key = {
            "marine-api.open-meteo.com": "open_meteo_marine",
            "api.open-meteo.com": "open_meteo_weather",
            "coastwatch.noaa.gov": "noaa_viirs_chl",
        }.get(host)
        if host == "incois.gov.in":
            return httpx.Response(
                200,
                json=json.loads(
                    (SNAPSHOT_DIR / "incois_pfz_lines.json").read_text(encoding="utf-8")
                ),
            )
        if key is None:
            return httpx.Response(404)
        return httpx.Response(
            200,
            json=json.loads((SNAPSHOT_DIR / "kochi" / f"{key}.json").read_text(encoding="utf-8")),
        )

    monkeypatch.setattr(base, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(
        base,
        "client",
        lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=2.0),
    )
    base._inflight.clear()
    # freeze "now" to the snapshot day so 'tomorrow morning' is covered by the payloads
    manifest = json.loads((SNAPSHOT_DIR / "manifest.json").read_text(encoding="utf-8"))
    snap_day = datetime.fromisoformat(manifest["created_at"]).astimezone(UTC)
    import marine.tools.windows as w

    real = w.named_window
    monkeypatch.setattr(
        w,
        "named_window",
        lambda day="tomorrow", part="morning", now=None: real(day, part, now=snap_day),
    )
    import marine.agents.specialists as sp

    monkeypatch.setattr(sp, "named_window", w.named_window)


class FakeLLM:
    """Scripted model: returns canned text; `hallucinate` adds a number not in any ledger."""

    name = "fake"

    def __init__(self, hallucinate: bool = False):
        self.hallucinate, self.calls = hallucinate, 0

    async def complete(self, system, user, *, json_mode=False, max_tokens=1024):
        return json.dumps(
            {
                "language": "ta",
                "english_query": "Is it safe off Kochi tomorrow morning?",
                "intent": "safety",
                "location_name": "Kochi",
                "day": "tomorrow",
                "part": "morning",
            }
        )

    async def stream(self, system, user, *, max_tokens=1024):
        self.calls += 1
        if self.hallucinate and self.calls == 1:
            yield "Verdict first. Waves 4.7 m and wind 41 kt expected."  # invented
        else:
            yield "The engine's verdict applies. Conditions are as listed in the brief."


# -- planner fast path --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "q,intent,loc",
    [
        ("Is it safe to go out from Kochi tomorrow morning?", Intent.SAFETY, "Kochi"),
        ("where are the fish near paradip", Intent.PFZ, "Paradip"),
        ("how far is the sri lanka border from rameswaram", Intent.BOUNDARY, "Rameswaram"),
        ("what is the wave height off chennai tonight", Intent.CONDITIONS, "Chennai"),
        (
            "is the catch declining near port blair because of chlorophyll",
            Intent.CHLOROPHYLL,
            "Port Blair",
        ),
    ],
)
def test_fast_path_intents_and_locations(q, intent, loc):
    p = fast_plan(q)
    assert p is not None and p.source == "fast_path"
    assert p.intent == intent and p.location.name == loc


def test_fast_path_extracts_window_vessel_heading_speed():
    p = fast_plan("can i go fishing off veraval today evening in my trawler heading 270 at 6 knots")
    assert (p.day, p.part) == ("today", "evening")
    assert p.vessel == "mechanised" and p.heading_deg == 270 and p.speed_kt == 6


def test_fast_path_defers_when_no_location_or_non_latin():
    assert fast_plan("is it safe tomorrow") is None
    assert fast_plan("What does a 2 metre swell mean?") is None
    assert fast_plan("நாளை கடலுக்கு போகலாமா?") is None


async def test_make_plan_without_llm_degrades_to_clarify():
    p = await make_plan("நாளை கடலுக்கு போகலாமா?", None)
    assert p.intent == Intent.CLARIFY and p.language == "ta" and p.clarify_question


def test_dag_shape_for_safety_runs_fetches_in_parallel_then_risk():
    t = tasks_for(fast_plan("is it safe off kochi tomorrow"))
    ids = {x.id: x for x in t}
    assert ids["ocean"].depends_on == [] and ids["geo"].depends_on == []
    assert set(ids["risk"].depends_on) == {"ocean", "geo"}
    assert "risk" in ids["synthesis"].depends_on


def test_dag_shape_for_pfz_has_no_risk_node():
    t = tasks_for(fast_plan("where are the fish near paradip"))
    assert {x.id for x in t} == {"geo", "analytics", "synthesis"}


# -- verifier --------------------------------------------------------------------------------------


def _brief(**kw) -> Brief:
    return Brief(
        intent=Intent.SAFETY,
        language="en",
        location="Kochi",
        allowed_numbers={1.02, 5.9, 4.78, 5.0, 1.5, 2.5, 19.0, 27.0, 42.1, 228.0},
        **kw,
    )


def test_verify_accepts_ledger_numbers_and_roundings():
    v = verify("Waves 1.02 m, wind 5.9 kt, PFZ 42.1 km at 228°. Waves about 1 m.", _brief())
    assert v.ok


def test_verify_rejects_a_number_not_in_the_ledger():
    v = verify("Waves 1.02 m and wind 23 kt.", _brief())
    assert not v.ok and v.unsupported == ["23"]


def test_verify_ignores_dates_times_and_small_counts():
    v = verify("Thu 17 Sep 05:00–12:00 IST, advisory 2026-09-15. There are 3 zones.", _brief())
    assert v.ok


def test_verify_handles_devanagari_and_tamil_digits():
    assert verify("अलैगल् १.०२ m", _brief()).ok
    assert not verify("अलैगल् ३.५ m", _brief()).ok


def test_verify_catches_english_contradiction_of_no_go():
    v = verify("Do not sail. Actually it is safe to go.", _brief(verdict="DO NOT SAIL"))
    assert not v.ok and v.contradiction


def test_template_answer_is_valid_by_construction():
    b = _brief(
        verdict="CAUTION",
        vessel="traditional",
        window="Thu 17 Sep 05:00–12:00 IST",
        reasons=["visibility 4.78 km ≤ caution threshold 5 km"],
        conditions=["wave height 1.02 m [obs_0001; x; grid 8 km; 2 min ago; current]"],
    )
    assert verify(template_answer(b), b).ok


# -- graph end to end ------------------------------------------------------------------------


async def test_graph_deterministic_mode_answers_safety_question(live_from_snapshot):
    out = await ask(
        "Is it safe to go out from Kochi tomorrow morning?", llm=None, ctx=ToolContext()
    )
    plan, ans, verdict = out["plan"], out["answer"], out["verdict"]
    assert plan.source == "fast_path" and plan.intent == Intent.SAFETY
    assert verdict is not None and ans.verdict == verdict.label
    assert ans.source == "template" and ans.verification.ok
    nodes = {e["node"] for e in out["events"]}
    assert {"planner", "ocean_weather", "geospatial", "risk_engine", "synthesis", "total"} <= nodes
    assert len(out["ctx"].ledger.observations) > 50


async def test_graph_with_fake_llm_uses_model_answer(live_from_snapshot):
    out = await ask(
        "Is it safe to go out from Kochi tomorrow morning?", llm=FakeLLM(), ctx=ToolContext()
    )
    assert out["answer"].source == "llm" and out["answer"].verification.ok


async def test_graph_verifier_rejects_hallucinated_numbers_then_accepts_retry(live_from_snapshot):
    llm = FakeLLM(hallucinate=True)
    out = await ask("Is it safe to go out from Kochi tomorrow morning?", llm=llm, ctx=ToolContext())
    ans = out["answer"]
    assert llm.calls == 2  # first draft rejected, retry accepted
    assert ans.source == "llm_retry" and ans.verification.ok
    assert "4.7" not in ans.text and "41" not in ans.text


async def test_graph_pfz_question_skips_risk_and_reports_zones(live_from_snapshot):
    out = await ask("where are the fish near kochi", llm=None, ctx=ToolContext())
    assert out["verdict"] is None
    assert out["geo"] is not None and out["geo"].pfz
    assert "PFZ" in out["answer"].text


async def test_graph_clarify_when_no_location(live_from_snapshot):
    out = await ask("is it safe tomorrow", llm=None, ctx=ToolContext())
    assert out["plan"].intent == Intent.CLARIFY
    assert out["answer"].text and out.get("verdict") is None


async def test_graph_survives_llm_failure(live_from_snapshot):
    class Broken(FakeLLM):
        async def stream(self, system, user, *, max_tokens=1024):
            raise LLMUnavailable("boom")
            yield ""

    out = await ask(
        "Is it safe to go out from Kochi tomorrow morning?", llm=Broken(), ctx=ToolContext()
    )
    assert out["answer"].source == "template_fallback" and out["answer"].verification.ok


def test_verify_rejects_verdict_words_when_no_verdict_exists():
    b = Brief(intent=Intent.PFZ, language="en", location="Kochi", allowed_numbers={42.1})
    assert not verify("GO. The nearest zone is 42.1 km away.", b).ok
    assert not verify("It is safe; the zone is 42.1 km away.", b).ok
    assert verify("Go 42.1 km south-west to the nearest zone.", b).ok  # lower-case verb is fine


def test_dag_for_boundary_question_runs_ocean_and_risk():
    t = tasks_for(
        fast_plan("how far is the sri lanka border from rameswaram heading 90 at 8 knots")
    )
    assert {x.id for x in t} == {"ocean", "geo", "risk", "synthesis"}
