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
from marine.tools import LocationQuery, ToolContext, resolve_location

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


# Regressions found by the fisherman question bank (data/question_bank, run 2026-10-16).


def test_fast_path_prefers_exact_place_over_an_early_fuzzy_span():
    # "i have" used to match inside "vash[i have]li" and win before "Veraval" was reached.
    p = fast_plan("I have a 15 metre boat at Veraval, is it ok to go out tomorrow early morning?")
    assert p.location.name == "Veraval" and p.vessel == "motorised"
    r = resolve_location(LocationQuery(name="i have"))
    assert r is None or "haveli" not in r.name.lower()


def test_fast_path_this_afternoon_is_today_and_know_is_not_now():
    assert fast_plan("How strong is the wind off Mangalore this afternoon?").day == "today"
    assert fast_plan("do you know the wave height at chennai").day == "tomorrow"


def test_fast_path_finding_fish_is_pfz_even_with_a_safety_phrase():
    p = fast_plan("Which direction should I go from Malpe to find fish?")
    assert p.intent == Intent.PFZ and p.location.name == "Malpe"
    assert fast_plan("Should I go fishing from Kochi tomorrow?").intent == Intent.SAFETY


def test_fast_path_romanised_hindi_is_answered_in_hindi():
    p = fast_plan("Kal subah Porbandar se boat nikalna safe hai kya?")
    assert p.language == "hi" and p.intent == Intent.SAFETY and p.location.name == "Porbandar"
    assert (p.day, p.part) == ("tomorrow", "morning")
    assert fast_plan("Is it safe to go out from Kochi tomorrow?").language == "en"


def _gemini_mock(seen: list[str], exhausted: set[str]) -> httpx.MockTransport:
    def handler(req: httpx.Request) -> httpx.Response:
        model = req.url.path.split("/models/")[1].split(":")[0]
        seen.append(model)
        if model in exhausted:
            return httpx.Response(
                429,
                json={"error": {"code": 429, "status": "RESOURCE_EXHAUSTED", "details": [
                    {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "3600s"}
                ]}},
            )
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "ok"}]}}]})

    return httpx.MockTransport(handler)


async def test_gemini_falls_back_when_a_models_daily_quota_is_spent():
    from marine.agents import llm as llm_mod

    llm_mod._PARKED.clear()
    seen: list[str] = []
    g = llm_mod.GeminiLLM("k", "primary", fallbacks=["backup"])
    g.transport = _gemini_mock(seen, exhausted={"primary"})
    assert await g.complete("s", "u") == "ok"
    assert seen == ["primary", "backup"] and g.model == "backup"
    seen.clear()
    assert await g.complete("s", "u") == "ok"
    assert seen == ["backup"]  # the spent model stays parked for its retryDelay
    llm_mod._PARKED.clear()


async def test_gemini_drops_thinking_config_for_models_that_reject_it():
    # gemini-3.5-flash-lite answers 400 INVALID_ARGUMENT to thinkingConfig{thinkingBudget: 0}.
    from marine.agents import llm as llm_mod

    llm_mod._NO_THINKING_CONFIG.clear()
    bodies: list[dict] = []

    def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content)
        bodies.append(body)
        if "thinkingConfig" in body["generationConfig"]:
            err = {"code": 400, "message": "Request contains an invalid argument.",
                   "status": "INVALID_ARGUMENT"}
            return httpx.Response(400, json={"error": err})
        ok = {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}
        return httpx.Response(200, json=ok)

    g = llm_mod.GeminiLLM("k", "lite")
    g.transport = httpx.MockTransport(handler)
    assert await g.complete("s", "u") == "ok"
    assert len(bodies) == 2  # refused once, resent without thinkingConfig
    bodies.clear()
    assert await g.complete("s", "u") == "ok"
    assert len(bodies) == 1 and "thinkingConfig" not in bodies[0]["generationConfig"]
    llm_mod._NO_THINKING_CONFIG.clear()


async def test_gemini_raises_unavailable_when_every_model_is_spent():
    from marine.agents import llm as llm_mod

    llm_mod._PARKED.clear()
    g = llm_mod.GeminiLLM("k", "a", fallbacks=["b"])
    g.transport = _gemini_mock([], exhausted={"a", "b"})
    with pytest.raises(LLMUnavailable, match="every model unavailable"):
        await g.complete("s", "u")
    llm_mod._PARKED.clear()


def test_fast_path_recognises_route_questions_and_which_zone():
    p = fast_plan("What is the safest way from Rameswaram to the fishing zone?")
    assert p.intent == Intent.ROUTE and p.location.name == "Rameswaram" and p.pfz_index is None
    assert fast_plan("best route from kochi to PFZ #2").pfz_index == 2
    assert fast_plan("how do i reach the second zone from chennai").pfz_index == 2
    # A route phrase beats the find-fish pattern; without one, finding fish is still PFZ.
    assert fast_plan("best route to find fish from malpe").intent == Intent.ROUTE
    assert fast_plan("Which direction should I go from Malpe to find fish?").intent == Intent.PFZ


def test_dag_for_route_fetches_in_parallel_then_grades_the_route():
    p = fast_plan("best route from kochi to the fishing zone")
    tasks = {t.id: t for t in tasks_for(p)}
    assert {"ocean", "geo", "risk", "synthesis"} <= set(tasks)
    assert "plan_sea_route" in tasks["geo"].tool
    assert set(tasks["risk"].depends_on) == {"ocean", "geo"}


def test_route_conditions_raise_the_verdict_inputs_with_period_from_the_same_node():
    from marine.ledger import EvidenceLedger, Observation
    from marine.risk.rules import RiskInputs
    from marine.tools.safety import merge_route_conditions

    ledger, t = EvidenceLedger(), datetime.now(UTC)

    def ob(var, val, unit, node):
        return ledger.add(Observation(variable=var, value=val, unit=unit, source="grid",
                                      valid_time=t, fetched_at=t, distance_km=1.0,
                                      confidence=1.0, note=node))

    ids = [o.id for o in (
        ob("route_wave_height", 1.2, "m", "node A"), ob("route_wave_period", 9.0, "s", "node A"),
        ob("route_wave_height", 2.1, "m", "node B"), ob("route_wave_period", 5.0, "s", "node B"),
        ob("route_wind_speed", 22.0, "kt", "node B"),
    )]
    worse_at_sea = RiskInputs(wave_height_m=0.8, wave_period_s=8.0, wind_kt=10.0)
    merge_route_conditions(worse_at_sea, ledger, ids)
    # The 2.1 m wave is paired with node B's 5 s period, not node A's 9 s.
    assert (worse_at_sea.wave_height_m, worse_at_sea.wave_period_s) == (2.1, 5.0)
    assert worse_at_sea.wind_kt == 22.0
    worse_at_harbour = RiskInputs(wave_height_m=3.0, wave_period_s=8.0, wind_kt=30.0)
    merge_route_conditions(worse_at_harbour, ledger, ids)
    assert (worse_at_harbour.wave_height_m, worse_at_harbour.wind_kt) == (3.0, 30.0)


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
    # The template quotes chlorophyll with its grid distance and a signed z-score; both must
    # pass the verifier, or the no-model fallback marks its own answer unverified.
    assert out["answer"].verification.ok, out["answer"].verification.unsupported


def test_general_knowledge_may_echo_the_askers_own_number_but_forecasts_may_not():
    from marine.agents.planner import Plan
    from marine.agents.synthesis import build_brief
    from marine.ledger import EvidenceLedger

    q = "What does a 2 metre swell mean for a small boat?"
    gk = Plan(language="en", english_query=q, intent=Intent.GENERAL_KNOWLEDGE)
    b = build_brief(gk, EvidenceLedger(), None, None, None, None)
    assert verify("A 2-metre swell makes a small boat roll heavily.", b).ok
    # A forecast question must not let the model "confirm" the asker's premise.
    fc = Plan(language="en", english_query="waves will be 0.5 m at Kochi tomorrow, right?",
              intent=Intent.CONDITIONS)
    b2 = build_brief(fc, EvidenceLedger(), None, None, None, None)
    assert not verify("Yes, waves will be 0.5 m.", b2).ok


async def test_graph_route_question_routes_to_the_nearest_zone_and_grades_it(live_from_snapshot):
    from marine.geo.boundaries import position_status

    out = await ask("what is the best route from kochi to the fishing zone", llm=None,
                    ctx=ToolContext())
    r = out["geo"].route
    assert r is not None and r.found and r.destination == "PFZ #1"
    assert len(r.path) >= 2 and all(position_status(*p).zone == "eez" for p in r.path)
    assert out["verdict"] is not None  # a route is graded by the deterministic engine
    ledger = out["ctx"].ledger
    assert all(ledger.get(i) is not None for i in r.observation_ids)
    ans = out["answer"]
    assert ans.verification.ok, ans.verification.unsupported
    assert "not a navigation chart" in ans.text


async def test_route_falls_back_to_the_harbour_forecast_and_says_so(live_from_snapshot,
                                                                    monkeypatch):
    import marine.tools.route as tr

    async def no_grid(_url):
        return None

    monkeypatch.setattr(tr, "_fetch", no_grid)
    out = await ask("what is the best route from kochi to the fishing zone", llm=None,
                    ctx=ToolContext())
    r = out["geo"].route
    assert r.found and r.sea_state_source == "harbour_only"
    assert any("route sea state" in d for d in out["answer"].degradation)
    assert out["answer"].verification.ok


async def test_graph_chlorophyll_template_passes_its_own_verification(live_from_snapshot):
    out = await ask("why has my catch dropped near kochi", llm=None, ctx=ToolContext())
    assert out["answer"].verification.ok, out["answer"].verification.unsupported


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
