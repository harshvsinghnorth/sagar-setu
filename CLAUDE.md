# Marine Intelligence Platform

Conversational decision support for Indian small-craft fishermen. A user asks a question
in their own language — "is it safe to go out tomorrow morning?" — and the system fetches
live marine data from Indian government sources, reasons across them, and answers in that
same language with a map and the evidence behind every number.

Built for the ISRO/INCOIS agentic marine intelligence problem statement (SIH).

---

## The five rules

These are not preferences. Violating any of them is a bug, even if the code works.

**1. A language model never decides whether it is safe to go to sea.**
Safety verdicts come from `src/marine/risk/` — plain Python, deterministic, unit-tested,
under 50 ms. The LLM receives the verdict and explains it in the user's language. It does
not compute it, adjust it, or soften it. People act on this advice.

**2. Every number that reaches the user is in the evidence ledger first.**
No tool returns a bare float. Tools return `Observation` objects carrying value, source,
valid time, distance from the query point, and fetch latency. The synthesis step may only
cite values present in the ledger; the verifier pass strips anything else.

**3. Cache first, network second, snapshot always available.**
Any fetch that exceeds 2 s falls back down the source chain, then to the frozen snapshot in
`data/snapshots/`. The system must produce a complete, honest answer with the network
unplugged. It says when it is serving cached or snapshot data — it never hides degradation.

**4. Four agents. Not nine.**
Planner, Ocean & Weather, Geospatial & Boundary, Analytics & Causal, Synthesis & Verify.
The problem statement lists nine *roles*; those are capabilities, not processes. Do not add
an agent. If a capability is missing, it belongs in the tool belt as ordinary Python.

**5. Never reimplement the PFZ product.**
INCOIS publishes an operational Potential Fishing Zone advisory validated against two
decades of catch data. We consume it. We do not train a model to predict fishing zones.
Our contribution is reasoning over it, not replacing it.

---

## Architecture

```
  Chat · Map · Alerts                    ← React + MapLibre
        ↓
  Language gateway (detect → translate)  ← Bhashini, IndicTrans2 fallback
        ↓
  Planner  ── the only free-form LLM step, emits a typed task DAG
        ↓
  ┌──────────┬──────────┬──────────┬──────────┐
  │ Ocean &  │Geospatial│Analytics │Synthesis │  ← four specialists
  │ Weather  │& Boundary│& Causal  │& Verify  │
  └──────────┴──────────┴──────────┴──────────┘
        ↓
  Risk engine — DETERMINISTIC, no model                    ⟵ evidence ledger
        ↓                                                     runs alongside
  Tool belt — ~15 typed Python functions                      all of this
        ↓
  Cache-first data layer → INCOIS · IMD · Open-Meteo · Copernicus
```

The load-bearing line is between the specialists and the risk engine. Above it, models plan
and explain. Below it, ordinary Python fetches and decides. Latency, debuggability and
trustworthiness all follow from keeping that line clean.

### Agent responsibilities

| Agent | Owns | Must not |
|---|---|---|
| **Planner** | Resolving vague location refs to coordinates, emitting a task DAG with explicit dependencies so independent fetches run in parallel | Emit prose; emit a sequential chain when fetches are independent |
| **Ocean & Weather** | Reconciling sources on different grids, interpolating to the query point, flagging disagreement | Silently average conflicting sources |
| **Geospatial & Boundary** | Point-in-polygon against EEZ/IMBL/MPA, *predictive* geofencing (project heading 90 min forward), A* route search | Warn only after a crossing has happened |
| **Analytics & Causal** | Anomaly detection over chlorophyll/SST against multi-year baseline, naming the mechanism behind a change | Assert causation the data cannot support |
| **Synthesis & Verify** | Drafting the answer, then a second pass checking every numeric claim against the ledger | Let an unsupported claim through |

---

## Project layout

```
├── CLAUDE.md
├── pyproject.toml
├── .env.example
├── data/
│   ├── static/          # EEZ, IMBL, MPA polygons — committed, rarely change
│   ├── snapshots/       # frozen demo data, committed, the offline fallback
│   └── cache/           # gitignored
├── src/marine/
│   ├── config.py
│   ├── fixtures.py      # test harbours — see below
│   ├── ledger.py        # Observation, EvidenceLedger
│   ├── sources/
│   │   ├── base.py      # Source protocol, retry, timeout, fallback chain
│   │   ├── incois_erddap.py
│   │   ├── incois_pfz.py
│   │   ├── imd.py
│   │   ├── open_meteo.py
│   │   └── copernicus.py
│   ├── tools/           # typed Pydantic tools, the agent-callable surface
│   ├── risk/
│   │   ├── thresholds.py
│   │   └── rules.py     # heavily unit-tested
│   ├── geo/             # point-in-polygon, geofence, routing
│   ├── agents/          # planner + four specialists
│   ├── graph.py         # LangGraph state machine
│   └── api.py           # FastAPI + SSE
├── tests/
└── web/                 # React + Vite + MapLibre GL
```

---

## Data sources

Verify every one of these before writing code against it. They were read from documentation,
not tested live. If an endpoint needs credentials we don't have, say so immediately rather
than building around a guess.

| Source | Gives | Access |
|---|---|---|
| INCOIS ERDDAP `erddap.incois.gov.in/erddap` | SST, winds, currents, Argo. NetCDF/CSV/JSON + WMS | Open, REST + griddap |
| INCOIS PFZ `incois.gov.in/MarineFisheries` | Potential Fishing Zone advisories, 12 sectors, 10 Indian languages | WebGIS + text pages; scrape and cache |
| IMD `api.imd.gov.in/api/v1/` | District warnings, nowcast, `cyclone_track`, `cyclone_cou`, lightning, marine forecast | Appears open, no key documented |
| Open-Meteo `marine-api.open-meteo.com/v1/marine` | Wave height/period/direction, swell, SST, currents, tides. 8-day hourly | Free, no key |
| Copernicus Marine | Chlorophyll-a (`GLOBAL_ANALYSISFORECAST_BGC_001_028`), physics (`PHY_001_024`) | Free account, Python toolbox |
| Marine Regions (VLIZ) | Indian EEZ, Andaman EEZ, boundary lines | Shapefile/GeoJSON, static |
| Bhashini / IndicTrans2 | Translation + ASR, 22 scheduled languages | Bhashini needs keys; IndicTrans2 open weights |

**Open-Meteo is the reliability floor.** It is the one source that answers in ~300 ms from a
bad conference-centre connection, so it backs every other source in the fallback chain.

---

## The evidence ledger

Every tool returns observations in this shape. This is the single most important data
structure in the project — it is what makes the system explainable and what stops
hallucination.

```python
class Observation(BaseModel):
    variable: str          # "significant_wave_height"
    value: float
    unit: str              # "m"
    source: str            # "open_meteo/mfwam"
    valid_time: datetime   # when the observation/forecast is FOR
    fetched_at: datetime   # when we got it
    distance_km: float     # from the query point to the nearest grid node
    confidence: float      # 0-1, lowered when we fell back down the chain
    note: str | None       # "served from snapshot, network unavailable"
```

Render this in the UI under every answer. Show staleness prominently — a forecast six hours
old and one six minutes old must not look the same on screen. Marine information has a
half-life and the interface should show that it knows.

---

## Risk thresholds

Starting values for small craft. **Calibrate against INCOIS's published small-craft warning
criteria and cite that calibration** — replace these numbers with sourced ones as soon as
someone finds the official document.

| Parameter | Go | Caution | Do not sail |
|---|---|---|---|
| Significant wave height | < 1.5 m | 1.5 – 2.5 m | > 2.5 m |
| Sustained wind | < 19 kt | 19 – 27 kt | > 27 kt |
| Sea steepness (Hs/T²) | low | short-period swell | breaking-sea regime |
| Lightning proximity | none < 50 km | 50–100 km closing | any strike < 50 km |
| Cyclone cone of uncertainty | no intersect | intersect 72–120 h | intersect < 48 h |
| Visibility | > 5 km | 2 – 5 km | < 2 km |

**Worst-of wins. Never average.** One do-not-sail parameter makes the whole verdict
do-not-sail, however benign the others look. Averaging across six parameters is how you
write a system that sends someone out under a thunderhead because the waves were calm.

Vessel class matters: keep three profiles (traditional < 12 m, motorised 12–20 m,
mechanised > 20 m) with separate threshold tables. Ask for vessel length once at onboarding.

---

## Test locations

Never hardcode a single location. Everything must work at all of these — they span different
grid coverage, different INCOIS sectors, and different monsoon regimes.

```python
HARBOURS = {
    "kochi":     (9.97,  76.28),   # Kerala, Arabian Sea
    "veraval":   (20.90, 70.37),   # Gujarat, high trawler density
    "chennai":   (13.09, 80.29),   # Tamil Nadu, Bay of Bengal
    "paradip":   (20.26, 86.67),   # Odisha, cyclone-exposed
    "port_blair":(11.62, 92.73),   # Andamans, sparse grid coverage
}
```

The Gulf of Mannar near the India–Sri Lanka IMBL is the geofencing test case, and the one
worth getting right — fishermen are detained there every year.

---

## Latency budget

Write this on the wall. A fisherman-facing tool that takes 40 s looks broken regardless of
answer quality, and 40 s is exactly what a naive nine-agent chain costs.

| Stage | Budget |
|---|---|
| Language detect + translate in | 300 ms |
| Planner → task DAG | 600 ms |
| Tool fan-out, parallel, warm cache | 800 ms |
| Risk engine | < 50 ms |
| Synthesis, first token | 700 ms |
| **First token on screen** | **≈ 2.4 s** |

Everything in the fan-out that can run concurrently must. A sequential chain for independent
fetches is a bug in the planner prompt, not a fact about the problem.

---

## Conventions

- **Python 3.11+**, `uv` for dependency management, `ruff` for lint and format.
- **Pydantic for every tool signature.** A malformed tool call should fail loudly at the
  boundary, not become a wrong number in an answer.
- **`xarray` + `netCDF4`** for gridded data. It's the native idiom for ERDDAP and Copernicus.
- **Tests before agents.** `src/marine/risk/` and `src/marine/geo/` are pure functions with
  no LLM in sight — they get real unit tests with real fixtures. Agent behaviour gets
  smoke tests, not assertions on exact wording.
- **Async everywhere in `sources/`.** The fan-out depends on it.
- **Type hints are not optional** in `tools/` and `risk/`.
- Frontend: React + Vite + **MapLibre GL** (not Mapbox — no token means one less thing that
  can fail during a demo). `deck.gl` only if raster overlays need it.

### Commands

```bash
uv sync                          # install
uv run pytest                    # tests
uv run pytest tests/test_risk.py # the ones that matter most
uv run ruff check --fix .
uv run uvicorn marine.api:app --reload
cd web && npm run dev
```

---

## Scope

**Build these five.** They are the demo.

1. PFZ query with map overlay, bearing and distance from the user's harbour
2. Safety go/no-go through the deterministic engine, explained in plain language
3. Geofence warning against IMBL and EEZ, including the predictive version
4. A full round trip in Tamil or Hindi, typed
5. The evidence ledger, visible in the interface

**If time allows:** route optimisation (A* over a sea grid, cost from wave/wind/current
against heading), multi-turn refinement, the productivity-decline causal query, a background
vessel monitor pushing unprompted alerts.

**Do not build:** a custom PFZ model, any LLM fine-tuning, a native mobile app, real-time
satellite ingestion pipelines, live voice input. On voice specifically — the accessibility
argument is real, but Tamil ASR over engine noise will fail in front of judges, and a failed
voice demo costs more than no voice demo. One scripted pre-recorded exchange, labelled
honestly, if at all.

---

## Build order

Each phase de-risks the next. Do not skip ahead.

1. **Prove the data, then freeze it.** Nothing but verifying endpoints. Record exact request
   shapes and response schemas. Cache a week of real data for the five harbours. End with a
   snapshot you could demo from with the network unplugged.
2. **Tools and the risk engine.** Fifteen typed functions, deterministic rules, unit tests.
   No LLM yet. You should be able to answer "is it safe off Kochi tomorrow" from a Python
   REPL with a full ledger in under a second.
3. **Planner and the graph.** LangGraph state machine, parallel fan-out, verifier pass.
   Budget time for prompt iteration.
4. **Map and interface.** MapLibre with PFZ overlay, EEZ/IMBL lines, vessel position, ledger
   panel. Streaming over SSE. Should have been started in parallel at phase 2.
5. **Language and stretch items.** Bhashini round trip with IndicTrans2 fallback. Then route
   optimisation first (demos best on a map), causal query second (demos best in conversation).
6. **Harden and rehearse.** Offline mode, error states, five-location testing, demo script.
   Rehearse with the wifi off at least twice.

---

## When you're stuck

Good answers this system should be able to give:

- "I don't have chlorophyll coverage for that point — the nearest observation is 340 km away."
- "INCOIS is not responding; this is Open-Meteo data from 14:00 IST, confidence reduced."
- "Wave height is within limits but there's lightning 30 km north-east and closing. Do not sail."

An invented number is never an acceptable answer. Degrading loudly beats failing silently,
and both beat a confident guess.
