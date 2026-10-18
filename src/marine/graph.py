"""The LangGraph state machine.

    plan ──┬─► ocean_weather ─┐
           ├─► geospatial ────┼─► risk ─► synthesis ─► END
           ├─► analytics ─────┘
           └────────────────────────────► synthesis (clarify / off-topic / knowledge)

The fan-out is decided by the typed DAG from `planner.tasks_for`; the three specialists
run in the same superstep, so they execute concurrently. `risk` is deterministic and only
does work for a safety intent. Every node appends a progress event so the API can stream
"Ocean & Weather agent: done (412 ms)" to the UI as it happens.
"""

from __future__ import annotations

import operator
import time
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph

from marine.agents import specialists
from marine.agents.llm import LLM, LLMUnavailable, get_llm
from marine.agents.planner import Intent, Plan, make_plan, tasks_for
from marine.agents.synthesis import (
    RESET,
    Answer,
    Brief,
    Verification,
    build_brief,
    synthesize,
)
from marine.risk.rules import RiskVerdict
from marine.tools import ToolContext
from marine.tools.locations import ResolvedLocation


class Event(TypedDict):
    node: str
    status: str  # started | done | failed | chunk
    ms: int
    detail: str


class State(TypedDict, total=False):
    query: str
    llm: Any  # LLM | None — not serialised; per-request object
    ctx: Any  # ToolContext (holds the ledger)
    on_chunk: Any  # async callback for streamed answer text
    plan: Plan
    ocean: specialists.OceanFinding | None
    geo: specialists.GeoFinding | None
    analytics: specialists.AnalyticsFinding | None
    verdict: RiskVerdict | None
    brief: Brief
    answer: Answer
    events: Annotated[list[Event], operator.add]
    started: float
    overrides: dict


def _ev(node: str, status: str, t0: float, detail: str = "") -> Event:
    return Event(
        node=node, status=status, ms=round((time.perf_counter() - t0) * 1000), detail=detail
    )


async def plan_node(state: State) -> dict:
    t0 = time.perf_counter()
    plan = await make_plan(state["query"], state.get("llm"))
    # Request-level overrides from the interface: the vessel class chosen at onboarding, and
    # a GPS position / heading / speed when the device supplies them. They fill gaps the
    # question left; an explicit value in the question still wins for heading and speed.
    ov = state.get("overrides") or {}
    if ov.get("vessel") and plan.vessel is None:
        plan.vessel = ov["vessel"]
    if plan.heading_deg is None and ov.get("heading_deg") is not None:
        plan.heading_deg = ov["heading_deg"]
    if plan.speed_kt is None and ov.get("speed_kt") is not None:
        plan.speed_kt = ov["speed_kt"]
    if plan.location is None and ov.get("lat") is not None and ov.get("lon") is not None:
        plan.location = ResolvedLocation(
            name=ov.get("location_name") or f"{ov['lat']:.2f}N {ov['lon']:.2f}E",
            lat=ov["lat"],
            lon=ov["lon"],
            match="device",
            score=1.0,
        )
        if plan.intent == Intent.CLARIFY:
            plan.intent = ov.get("fallback_intent", Intent.SAFETY)
            plan.clarify_question = None
    detail = f"{plan.source}; intent={plan.intent}; lang={plan.language}" + (
        f"; location={plan.location.name}" if plan.location else ""
    )
    return {"plan": plan, "events": [_ev("planner", "done", t0, detail)]}


def route(state: State) -> list[str]:
    plan = state["plan"]
    if (
        plan.intent in (Intent.CLARIFY, Intent.OFF_TOPIC, Intent.GENERAL_KNOWLEDGE)
        or plan.location is None
    ):
        return ["synthesis"]
    wanted = {t.agent for t in tasks_for(plan)}
    return [n for n in ("ocean_weather", "geospatial", "analytics") if n in wanted] or ["synthesis"]


async def ocean_node(state: State) -> dict:
    t0 = time.perf_counter()
    try:
        f = await specialists.ocean_weather(state["ctx"], state["plan"])
        return {
            "ocean": f,
            "events": [
                _ev("ocean_weather", "done", t0, f"{len(f.summary)} variables; sources {f.sources}")
            ],
        }
    except Exception as e:  # noqa: BLE001 — a specialist failure degrades the answer, never kills it
        return {
            "ocean": None,
            "events": [_ev("ocean_weather", "failed", t0, f"{type(e).__name__}: {e}")],
        }


async def geo_node(state: State) -> dict:
    t0 = time.perf_counter()
    try:
        f = await specialists.geospatial(state["ctx"], state["plan"])
        return {
            "geo": f,
            "events": [
                _ev(
                    "geospatial",
                    "done",
                    t0,
                    f"{len(f.pfz)} PFZ; zone={f.position.zone if f.position else '?'}"
                    + (
                        f"; route {f.route.distance_km} km to {f.route.destination}"
                        f" ({f.route.compute_ms:.0f} ms search)"
                        if f.route and f.route.found
                        else f"; route: {f.route.reason}"
                        if f.route
                        else ""
                    ),
                )
            ],
        }
    except Exception as e:  # noqa: BLE001
        return {
            "geo": None,
            "events": [_ev("geospatial", "failed", t0, f"{type(e).__name__}: {e}")],
        }


async def analytics_node(state: State) -> dict:
    t0 = time.perf_counter()
    try:
        f = await specialists.analytics(state["ctx"], state["plan"])
        return {
            "analytics": f,
            "events": [
                _ev(
                    "analytics",
                    "done",
                    t0,
                    f"z={f.z_score} trend={f.trend}" if f.latest else "no chlorophyll",
                )
            ],
        }
    except Exception as e:  # noqa: BLE001
        return {
            "analytics": None,
            "events": [_ev("analytics", "failed", t0, f"{type(e).__name__}: {e}")],
        }


def risk_node(state: State) -> dict:
    t0 = time.perf_counter()
    plan = state["plan"]
    if plan.intent not in (Intent.SAFETY, Intent.BOUNDARY, Intent.ROUTE) or plan.location is None:
        return {"verdict": None}
    v = specialists.risk(state["ctx"], plan, state.get("geo"))
    return {
        "verdict": v,
        "events": [
            _ev("risk_engine", "done", t0, f"{v.label} ({v.status}); engine {v.computed_ms} ms")
        ],
    }


async def synthesis_node(state: State) -> dict:
    t0 = time.perf_counter()
    plan: Plan = state["plan"]
    ctx: ToolContext = state["ctx"]
    brief = build_brief(
        plan,
        ctx.ledger,
        state.get("ocean"),
        state.get("geo"),
        state.get("analytics"),
        state.get("verdict"),
    )
    if plan.intent == Intent.CLARIFY:
        text = plan.clarify_question or "Which harbour are you asking about?"
        ans = Answer(
            text=text,
            language=plan.language,
            verdict=None,
            source="template",
            verification=Verification(ok=True),
            brief=brief,
        )
        if state.get("on_chunk"):
            await state["on_chunk"](text)
        return {"brief": brief, "answer": ans, "events": [_ev("synthesis", "done", t0, "clarify")]}
    llm: LLM | None = state.get("llm")
    ans = await synthesize(llm, brief, on_chunk=state.get("on_chunk"))
    if ans.source.startswith("template") and state.get("on_chunk"):
        await state["on_chunk"](RESET)
        await state["on_chunk"](ans.text)
    detail = f"{ans.source}; verified={ans.verification.ok}" + (
        f"; unsupported={ans.verification.unsupported}" if ans.verification.unsupported else ""
    )
    return {"brief": brief, "answer": ans, "events": [_ev("synthesis", "done", t0, detail)]}


def build_graph():
    g = StateGraph(State)
    g.add_node("planner", plan_node)
    g.add_node("ocean_weather", ocean_node)
    g.add_node("geospatial", geo_node)
    g.add_node("analytics", analytics_node)
    g.add_node("risk", risk_node)
    g.add_node("synthesis", synthesis_node)
    g.add_edge(START, "planner")
    g.add_conditional_edges(
        "planner", route, ["ocean_weather", "geospatial", "analytics", "synthesis"]
    )
    for n in ("ocean_weather", "geospatial", "analytics"):
        g.add_edge(n, "risk")
    g.add_edge("risk", "synthesis")
    g.add_edge("synthesis", END)
    return g.compile()


GRAPH = build_graph()


def _resolve_llm(llm: LLM | None | str) -> LLM | None:
    if isinstance(llm, str):
        try:
            llm = get_llm(llm)
            if llm.name == "none":
                return None
        except LLMUnavailable:
            return None
    return llm


def _initial_state(query: str, llm, ctx, on_chunk, overrides) -> State:
    return {
        "query": query,
        "llm": _resolve_llm(llm),
        "ctx": ctx or ToolContext(),
        "on_chunk": on_chunk,
        "overrides": overrides or {},
        "events": [],
        "started": time.perf_counter(),
    }


async def ask(
    query: str,
    *,
    llm: LLM | None | str = "auto",
    ctx: ToolContext | None = None,
    on_chunk=None,
    overrides: dict | None = None,
) -> State:
    """Run one question end to end. `llm="auto"` picks the configured provider; `None` means
    deterministic-only (templates)."""
    state = _initial_state(query, llm, ctx, on_chunk, overrides)
    t0 = state["started"]
    out = await GRAPH.ainvoke(state)
    out["events"] = out["events"] + [_ev("total", "done", t0)]
    return out


async def ask_streaming(
    query: str,
    *,
    llm: LLM | None | str = "auto",
    ctx: ToolContext | None = None,
    on_chunk=None,
    on_event=None,
    overrides: dict | None = None,
) -> State:
    """Like `ask`, but calls `on_event(event)` as each node finishes, so an API can stream
    agent progress before the answer exists. Returns the final state."""
    state = _initial_state(query, llm, ctx, on_chunk, overrides)
    t0 = state["started"]
    final: State = dict(state)  # type: ignore[assignment]
    async for update in GRAPH.astream(state, stream_mode="updates"):
        for _node, delta in update.items():
            if not delta:
                continue
            for ev in delta.get("events", []):
                if on_event:
                    await on_event(ev)
            for k, v in delta.items():
                if k == "events":
                    final["events"] = final.get("events", []) + v
                else:
                    final[k] = v
    total = _ev("total", "done", t0)
    final["events"] = final.get("events", []) + [total]
    if on_event:
        await on_event(total)
    return final
