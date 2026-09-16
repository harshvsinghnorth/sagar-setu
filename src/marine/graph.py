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
from marine.agents.synthesis import Answer, Brief, Verification, build_brief, synthesize
from marine.risk.rules import RiskVerdict
from marine.tools import ToolContext


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


def _ev(node: str, status: str, t0: float, detail: str = "") -> Event:
    return Event(
        node=node, status=status, ms=round((time.perf_counter() - t0) * 1000), detail=detail
    )


async def plan_node(state: State) -> dict:
    t0 = time.perf_counter()
    plan = await make_plan(state["query"], state.get("llm"))
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
                    f"{len(f.pfz)} PFZ; zone={f.position.zone if f.position else '?'}",
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
    if plan.intent != Intent.SAFETY or plan.location is None:
        return {"verdict": None}
    v = specialists.risk(state["ctx"], plan)
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


async def ask(
    query: str, *, llm: LLM | None | str = "auto", ctx: ToolContext | None = None, on_chunk=None
) -> State:
    """Run one question end to end. `llm="auto"` picks the configured provider; `None` means
    deterministic-only (templates)."""
    if isinstance(llm, str):
        try:
            llm = get_llm(llm)
            if llm.name == "none":
                llm = None
        except LLMUnavailable:
            llm = None
    t0 = time.perf_counter()
    state: State = {
        "query": query,
        "llm": llm,
        "ctx": ctx or ToolContext(),
        "on_chunk": on_chunk,
        "events": [],
        "started": t0,
    }
    out = await GRAPH.ainvoke(state)
    out["events"] = out["events"] + [_ev("total", "done", t0)]
    return out
