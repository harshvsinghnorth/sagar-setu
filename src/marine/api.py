"""FastAPI + SSE.

POST /ask streams one question: `agent` events as each node finishes, `chunk` events as
the answer is written, then one `result` event with everything the interface renders —
verdict (from the engine, never the prose), the ledger, degradation, PFZ and boundary
geometry, the projected track — then `done`. GET /geo/static serves the simplified EEZ and
IMBL lines once per session. On startup the PFZ advisory and the demo harbours are pre-warmed
so the first question does not pay the cold-fetch cost.

  uv run uvicorn marine.api:app --reload
"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from shapely.geometry import mapping, shape

from marine.agents.llm import LLMUnavailable, get_llm
from marine.agents.synthesis import RESET
from marine.config import ROOT, SNAPSHOT_DIR, STATIC_DIR, settings
from marine.fixtures import HARBOURS, KNOWN_PORTS
from marine.geo.boundaries import IMBL_TYPES
from marine.graph import ask_streaming
from marine.risk.thresholds import TABLES, VesselClass
from marine.sources import incois_pfz
from marine.sources.base import PointQuery
from marine.sources.open_meteo import OpenMeteoMarine, OpenMeteoWeather
from marine.tools import ToolContext
from marine.tools.windows import named_window

log = logging.getLogger("marine.api")


# -- startup: pre-warm -------------------------------------------------------------------------


async def prewarm() -> None:
    """PFZ (1 MB, ~4 s cold) and the demo harbours' forecasts, so a demo question is warm."""
    try:
        adv = await incois_pfz.fetch_pfz()
        log.info("prewarm: PFZ %s zones (%s)", len(adv.zones), adv.outcome.provenance)
    except Exception as e:  # noqa: BLE001
        log.warning("prewarm: PFZ failed: %s", e)
    s, e = named_window("tomorrow", "morning")
    marine, weather = OpenMeteoMarine(), OpenMeteoWeather()
    for name, (lat, lon) in HARBOURS.items():
        q = PointQuery(lat=lat, lon=lon, start=s, end=e)
        for src in (marine, weather):
            try:
                await src.fetch(q)
            except Exception as ex:  # noqa: BLE001
                log.warning("prewarm: %s %s failed: %s", name, src.name, ex)
    log.info("prewarm: done")


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(prewarm())
    yield
    task.cancel()


app = FastAPI(title="Sagar Setu", version="0.4.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# -- models --------------------------------------------------------------------------------------


class AskRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    vessel: VesselClass | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    heading_deg: float | None = Field(default=None, ge=0, lt=360)
    speed_kt: float | None = Field(default=None, ge=0, le=40)
    llm: str = "auto"


def _sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


# -- static geometry -------------------------------------------------------------------------------


@lru_cache(maxsize=1)
def static_geo() -> dict:
    """EEZ outline and IMBL lines, simplified to ~1 km so the browser loads ~200 KB, not 3 MB."""
    eez = json.loads((STATIC_DIR / "india_eez_polygon.geojson").read_text(encoding="utf-8"))
    eez_geom = shape(eez["features"][0]["geometry"]).simplify(0.01, preserve_topology=True)
    b = json.loads((STATIC_DIR / "india_eez_boundaries.geojson").read_text(encoding="utf-8"))
    imbl = []
    for f in b["features"]:
        p = f["properties"]
        if p.get("line_type") not in IMBL_TYPES:
            continue
        g = shape(f["geometry"]).simplify(0.005, preserve_topology=True)
        other = p.get("sovereign2") if p.get("sovereign1") == "India" else p.get("sovereign1")
        imbl.append(
            {
                "type": "Feature",
                "properties": {
                    "name": p["line_name"],
                    "other_state": other,
                    "line_type": p["line_type"],
                },
                "geometry": mapping(g),
            }
        )
    harbours = [
        {
            "type": "Feature",
            "properties": {"name": n.replace("_", " ").title(), "kind": k},
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
        }
        for src, k in ((HARBOURS, "test_harbour"), (KNOWN_PORTS, "port"))
        for n, (lat, lon) in src.items()
    ]
    return {
        "eez": {
            "type": "Feature",
            "properties": {"name": "Indian EEZ"},
            "geometry": mapping(eez_geom),
        },
        "imbl": {"type": "FeatureCollection", "features": imbl},
        "harbours": {"type": "FeatureCollection", "features": harbours},
    }


@app.get("/geo/static")
def geo_static() -> dict:
    return static_geo()


QUESTION_BANK = ROOT / "data" / "question_bank"


@app.get("/question-bank")
def question_bank() -> dict:
    """The fisherman question bank for the demo panel, with each question's result from the
    latest scored run (scripts/run_question_bank.py) attached when one exists."""
    bank = json.loads((QUESTION_BANK / "bank.json").read_text(encoding="utf-8"))
    results = QUESTION_BANK / "results.json"
    if results.exists():
        run = json.loads(results.read_text(encoding="utf-8"))
        status = {
            r["id"]: {"understood": r.get("understood"), "behaved": r.get("behaved")}
            for r in run.get("rows", [])
            if "error" not in r
        }
        for q in bank["questions"]:
            q["last_run"] = status.get(q["id"])
        bank["summary"] = run.get("summary")
    return bank


@app.get("/health")
def health() -> dict:
    try:
        provider = get_llm().name
    except LLMUnavailable:
        provider = "none"
    manifest = SNAPSHOT_DIR / "manifest.json"
    snap = (
        json.loads(manifest.read_text(encoding="utf-8"))["created_at"]
        if manifest.exists()
        else None
    )
    return {
        "ok": True,
        "llm": provider,
        "gemini_model": settings.gemini_model,
        "snapshot_created_at": snap,
        "vessel_classes": [v.value for v in VesselClass],
        "thresholds": {
            v.value: {
                "wave_height_m": [t.wave_height_m.caution, t.wave_height_m.no_go],
                "wind_kt": [t.wind_kt.caution, t.wind_kt.no_go],
                "visibility_km": [t.visibility_km.caution, t.visibility_km.no_go],
            }
            for v, t in TABLES.items()
        },
        "time": datetime.now(UTC).isoformat(),
    }


# -- the result payload ----------------------------------------------------------------------------


def _result_payload(state: dict) -> dict:
    plan, ans, verdict = state["plan"], state["answer"], state.get("verdict")
    ctx: ToolContext = state["ctx"]
    geo = state.get("geo")
    ocean = state.get("ocean")
    analytics = state.get("analytics")
    out: dict[str, Any] = {
        "query": state["query"],
        "plan": {
            "source": plan.source,
            "intent": plan.intent,
            "language": plan.language,
            "english_query": plan.english_query,
            "location": plan.location.model_dump() if plan.location else None,
            "day": plan.day,
            "part": plan.part,
            "vessel": plan.vessel,
            "heading_deg": plan.heading_deg,
            "speed_kt": plan.speed_kt,
        },
        "answer": {
            "text": ans.text,
            "language": ans.language,
            "source": ans.source,
            "verified": ans.verification.ok,
            "unsupported": ans.verification.unsupported,
        },
        "verdict": verdict.model_dump() | {"label": verdict.label} if verdict else None,
        "window": ans.brief.window,
        "degradation": ans.brief.degradation,
        "gaps": ans.brief.gaps,
        "ledger": {
            "observations": [o.model_dump() for o in ctx.ledger.observations],
            "missing": [m.model_dump() for m in ctx.ledger.missing],
            "sources": ctx.ledger.sources(),
            "degraded": ctx.ledger.degraded(),
        },
        "events": state.get("events", []),
        "map": {},
    }
    m = out["map"]
    if plan.location:
        m["location"] = {
            "lat": plan.location.lat,
            "lon": plan.location.lon,
            "name": plan.location.name,
        }
    if geo:
        m["pfz"] = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "uid": z.uid,
                        "state": z.state,
                        "advisory_date": z.advisory_date,
                        "distance_km": z.distance_km,
                        "bearing_deg": z.bearing_deg,
                        "compass": z.compass,
                        "rank": i,
                    },
                    "geometry": {
                        "type": "MultiLineString",
                        "coordinates": [[list(pt) for pt in part] for part in z.coordinates],
                    },
                }
                for i, z in enumerate(geo.pfz, 1)
            ],
        }
        m["pfz_bearings"] = [
            {
                "rank": i,
                "to": [z.nearest_lon, z.nearest_lat],
                "distance_km": z.distance_km,
                "bearing_deg": z.bearing_deg,
                "compass": z.compass,
                "state": z.state,
            }
            for i, z in enumerate(geo.pfz, 1)
        ]
        if geo.position and geo.position.nearest_imbl:
            n = geo.position.nearest_imbl
            m["nearest_imbl"] = {
                "name": n.name,
                "other_state": n.other_state,
                "distance_km": n.distance_km,
                "bearing_deg": n.bearing_deg,
                "compass": n.compass,
                "closest": [n.closest_lon, n.closest_lat],
                "zone": geo.position.zone,
            }
        if geo.crossing:
            c = geo.crossing
            m["track"] = {
                "points": [[lon, lat] for lat, lon in c.track],
                "crossing": [c.crossing_lon, c.crossing_lat]
                if c.crossing_lat is not None
                else None,
                "boundary": c.boundary,
                "minutes": c.minutes_to_crossing,
                "within_horizon": c.crosses_within_horizon,
            }
        if geo.route:
            r = geo.route
            m["route"] = {
                "found": r.found,
                "reason": r.reason,
                "destination": r.destination,
                "dest": [r.dest_lon, r.dest_lat],
                "points": [[lon, lat] for lat, lon in r.path],
                "distance_km": r.distance_km,
                "eta_min": r.eta_min,
                "min_imbl_km": r.min_imbl_km,
                "direct_crosses_border": r.direct_crosses_border,
                "sea_state_source": r.sea_state_source,
            }
    if ocean:
        m["conditions"] = {
            k: {
                "value": o.value,
                "unit": o.unit,
                "valid_time": o.valid_time.isoformat(),
                "provenance": o.provenance,
            }
            for k, o in ocean.summary.items()
        }
    if analytics and analytics.latest:
        out["analytics"] = {
            "latest": analytics.latest.value,
            "unit": analytics.latest.unit,
            "baseline_mean": analytics.baseline_mean,
            "baseline_sd": analytics.baseline_sd,
            "z_score": analytics.z_score,
            "trend": analytics.trend,
            "interpretation": analytics.interpretation,
        }
    return out


# -- /ask (SSE) ------------------------------------------------------------------------------------


@app.post("/ask")
async def ask_endpoint(req: AskRequest) -> StreamingResponse:
    queue: asyncio.Queue[tuple[str, Any] | None] = asyncio.Queue()

    async def on_chunk(text: str) -> None:
        if text == RESET:
            await queue.put(("reset", {}))
        else:
            await queue.put(("chunk", {"text": text}))

    async def on_event(ev: dict) -> None:
        await queue.put(("agent", ev))

    overrides = {
        k: v
        for k, v in {
            "vessel": req.vessel,
            "lat": req.lat,
            "lon": req.lon,
            "heading_deg": req.heading_deg,
            "speed_kt": req.speed_kt,
        }.items()
        if v is not None
    }

    async def run() -> None:
        try:
            state = await ask_streaming(
                req.query,
                llm=req.llm,
                ctx=ToolContext(),
                on_chunk=on_chunk,
                on_event=on_event,
                overrides=overrides,
            )
            await queue.put(("result", _result_payload(state)))
        except Exception as e:  # noqa: BLE001 — the client must always get a terminal event
            log.exception("ask failed")
            await queue.put(("error", {"message": f"{type(e).__name__}: {e}"}))
        finally:
            await queue.put(None)

    async def gen():
        task = asyncio.create_task(run())
        yield _sse("start", {"query": req.query, "time": datetime.now(UTC).isoformat()})
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                yield _sse(*item)
            yield _sse("done", {})
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
