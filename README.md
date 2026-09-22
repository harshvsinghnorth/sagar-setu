# Sagar Setu — Marine Intelligence Platform

Conversational decision support for Indian small-craft fishermen. Ask "is it safe to go out
tomorrow morning?" in your own language; the system fetches live marine data from Indian
government and open sources, reasons across them, and answers in that language with a map
and the evidence behind every number.

Built for the ISRO/INCOIS agentic marine intelligence problem statement (SIH 2026).

## Principles

1. **A language model never decides whether it is safe to go to sea.** Verdicts come from
   a deterministic, unit-tested engine in `src/marine/risk/`. The LLM only explains them.
2. **Every number shown is in the evidence ledger first** — with source, valid time,
   distance from the query point, staleness and confidence.
3. **Cache first, network second, snapshot always available.** Works with the network off,
   and says so.
4. **Four agents, not nine.** Planner, Ocean & Weather, Geospatial & Boundary,
   Analytics & Causal, Synthesis & Verify.
5. **INCOIS's PFZ advisory is consumed, never reimplemented.**

## Status

| Phase | State |
|---|---|
| 1 · Verify and freeze data sources | done — `docs/data-sources.md` |
| 2 · Tool belt + deterministic risk engine (no LLM) | done — 81 tests, `scripts/ask.py` answers in < 0.5 s warm |
| 3 · Planner, specialists, LangGraph, verifier | done — Gemini free tier by default, model-agnostic; Tamil/Hindi/English round trips |
| 4 · Map + interface (React + MapLibre, SSE) | done — chat, verdict badge, map with PFZ/IMBL/track, evidence ledger |
| 5 · Bhashini integration, multi-turn, route suggestion | next |
| 6 · Harden and rehearse offline | — |

How often is the verdict right? See [`docs/evaluation.md`](docs/evaluation.md) — day-ahead
do-not-sail warnings: 94% hit rate, 3% false-alarm ratio over 460 harbour-mornings of the 2026
monsoon (forecast vs model analysis; buoy validation pending). Regenerate with
`uv run python scripts/eval_report.py`.

The full narrative of how it was built is in [`docs/BUILD_LOG.md`](docs/BUILD_LOG.md).

## Quick start

```bash
uv sync --extra dev
uv run pytest                                   # 81 tests, no network needed
uv run python scripts/ask.py kochi              # go/no-go for tomorrow morning off Kochi
uv run python scripts/ask.py "fort kochi" --vessel motorised --day today --part afternoon
uv run python scripts/ask.py --lat 9.15 --lon 79.40 --heading 90 --speed 8   # Gulf of Mannar geofence
uv run python scripts/snapshot.py               # refresh the offline snapshot
uv run python scripts/chat.py "நாளை காலை கொச்சியில் இருந்து கடலுக்கு போகலாமா?"   # full pipeline, any language
```

The interface (two terminals):

```bash
uv run uvicorn marine.api:app --reload          # API on :8000
cd web && npm install && npm run dev            # UI on :5173
```

Set `GEMINI_API_KEY` in `.env` (free at aistudio.google.com) for the language model; without
it the system still answers in English from deterministic templates.

Copy `.env.example` to `.env`. All keys are optional and all are free tiers.

## Data sources (verified live 2026-09-15)

| Source | Role |
|---|---|
| Open-Meteo marine + weather | waves, swell, wind, visibility, SST, currents — the reliability floor |
| INCOIS PFZ (GeoServer WFS) | the day's Potential Fishing Zone lines |
| INCOIS landing centres + sectors, Marine Regions EEZ / IMBL | static, committed |
| NOAA CoastWatch VIIRS | chlorophyll-a |
| INCOIS ERDDAP Argo | coarse SST cross-check |
| IMD | cyclone / lightning — **needs an API key we do not yet have** |

Details, request shapes and gotchas: [`docs/data-sources.md`](docs/data-sources.md).

## Layout

```
src/marine/
  ledger.py        Observation, EvidenceLedger
  sources/         cache → network → snapshot chain; one module per source
  geo/             EEZ/IMBL geofencing (predictive), PFZ bearing/distance
  risk/            thresholds per vessel class, worst-of rules — no model
  tools/           typed, agent-callable functions
  agents/          llm provider layer, planner, specialists, synthesis + verifier
  graph.py         LangGraph state machine
  api.py           FastAPI + SSE
web/               React + Vite + MapLibre interface
data/static/       boundaries, sectors, landing centres
data/snapshots/    frozen demo data — the offline fallback
docs/              data-sources.md (reference), BUILD_LOG.md (narrative)
```
