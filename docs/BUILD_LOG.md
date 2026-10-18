# Sagar Setu — Build Log

A running journal of how this project was built: what we did, in what order, why, and
what we learned. Every step gets an entry as it happens. Newest entries at the bottom.

Conventions used in this log:
- **Decision** — a choice we made that shapes later work, with the reason.
- **Finding** — something we learned by testing, not by reading docs.
- **Blocked** — needs something from outside the codebase (a key, an account, a person).

---

## Day 1 — 2026-09-15

### Step 0 · Read the brief

Read `CLAUDE.md` end to end before touching anything. The five rules that govern every
later decision:

1. The LLM never decides safety — that is deterministic Python in `src/marine/risk/`.
2. Every number shown to the user lives in the evidence ledger first.
3. Cache first, network second, snapshot always available; degrade loudly.
4. Four agents, not nine.
5. Consume INCOIS's PFZ product; never reimplement it.

The build order is strict: **1** prove and freeze the data → **2** tools + risk engine
(no LLM) → **3** planner + LangGraph → **4** map + UI → **5** language + stretch →
**6** harden and rehearse. Each phase de-risks the next, so we do not skip ahead.

### Step 1 · Check the machine

Empty `Sagar Setu` folder. Found Python 3.12.2, Node 22.19, npm 10.9, git 2.47. `uv` was
missing — installed it via `pip install uv` (uv 0.12.14).

### Step 2 · Phase 1: verify every data source live, before writing code

CLAUDE.md says the sources table was read from documentation, not tested, and to verify
each one first. We hit every endpoint with `curl` from this machine and recorded exactly
what came back. Full request shapes and schemas are in `docs/data-sources.md`; the story
of how we got there is here.

**Open-Meteo** (marine + weather) — works first try, no key. Marine returns hourly
wave height/period/direction, swell, wind-waves, SST, currents for 8 days; weather gives
wind (we request knots), gusts, visibility, precipitation, weather code, CAPE.
- *Finding:* the response's lat/lon is the **grid node**, not our query point. Kochi
  snaps to (9.958, 76.208), about 8 km away. That number is exactly the `distance_km`
  the ledger must carry, so we record it rather than hide it.
- *Finding:* current velocity comes in **km/h**, not knots. Must convert.

**INCOIS ERDDAP** (`erddap.incois.gov.in`) — reachable, open, 16 gridded datasets.
- *Finding:* almost all of them are **stale**. Listing `allDatasets` with `maxTime`
  showed ASCAT winds end May 2023, OCM chlorophyll ends 2006, AVHRR SST ends 2011, and
  AMSR2 has a broken time axis (years 1901–1915). Only the Argo 10-day / monthly T-S
  fields are current (to 2026-07-30).
- *Decision:* ERDDAP cannot be the live wave/wind/SST source the brief implies.
  Open-Meteo carries that. Argo becomes a weak SST cross-check (1° grid, ~6 weeks old,
  `null` on coastal cells — the ledger will show all of that). The old datasets may serve
  as a climatology baseline for the Analytics agent later, if at all.

**IMD** (`api.imd.gov.in/api/v1/*`) — every endpoint (`cyclone_track`, `cyclone_cou`,
`nowcast`, `district_warning`, `lightning`, `marine_forecast`) returns
`401 {"error":"API key missing"}`. The public `mausam.imd.gov.in/api/*` variant answers
"Your IP … needs to be whitelisted".
- **Blocked:** we need an IMD API key. Until then there is **no live cyclone-track or
  lightning feed**.
- *Decision:* the risk engine still implements the cyclone and lightning rules with unit
  tests; the ledger reports those variables as "no source available" and the answer says
  so. Open-Meteo `cape` + thunderstorm weather codes (95–99) will be recorded as a
  *convective-risk proxy*, never labelled as lightning.

**INCOIS PFZ** — the page `incois.gov.in/MarineFisheries/PfzAdvisory` is prose only; no
data links. We tried the obvious guessed URLs (all 404), then searched and found the
geoportal at `incois.gov.in/geoportal/MFASPFZ/`. That is a Leaflet app, so we downloaded
its JS (`app.js`, `featureinfo.js`, `jsondata.js`) and read what it fetches.
- *Finding:* it calls an **undocumented GeoServer WFS** on `incois.gov.in/geoserver/`.
  `PFZ_Automation:pfzlines` returns the PFZ zones as GeoJSON MultiLineStrings —
  87 features, 1.1 MB, dated Julian day 257 of 2026 = **14 Sept 2026, yesterday**.
  So it is live. Properties: state, year, julian day, serial, length km.
- *Finding:* the same server has `PFZ_Sectors:sector_new` (14 sector polygons),
  `PFZ_LandingCentres:LandingCenters_29Apr2024` (1223 named landing centres with
  district and sector), and `PFZ_EEZ:indiaeez` (EEZ as lines).
- *Finding:* the landing-centre layer has BEARING / DISTANCE / DEPTH fields that look like
  the PFZ text advisory — but every one of them is stamped **2024-04-27**. They are
  frozen. We must not show them.
- *Decision:* bearing and distance to the nearest PFZ are **computed by us** from the
  live line geometry and the harbour position — ordinary great-circle maths, honest.
- *Finding:* on 2026-09-15 Tamil Nadu, Gujarat and Maharashtra had **no PFZ lines**.
  The system must say "no advisory for your sector today", never invent one.
- *Decision:* the 1223 landing centres become the planner's location resolver ("Vypeen",
  "Fort Kochi" → coordinates + sector) — no geocoding API needed.

**Marine Regions (VLIZ)** — WFS works. Pulled the India EEZ polygon (mrgid 8480, 1.85 MB,
38 s) and all EEZ boundary lines where India is a party (941 KB). The first boundary
feature starts at (79.53 E, 9.10 N): the India–Sri Lanka line through Palk Bay / Gulf of
Mannar — the geofencing test case named in the brief.
- *Decision:* static, slow to fetch → committed to `data/static/`, never fetched at runtime.

**Copernicus Marine** — needs a registered (free) account; the Python toolbox exists.
- **Blocked (optional):** register at marine.copernicus.eu if we want BGC/physics.
- *Decision:* look for an open chlorophyll substitute so nothing depends on it.

**NOAA CoastWatch ERDDAP** — queried `allDatasets` for chlorophyll sets with recent
`maxTime`. `noaacwNPPN20VIIRSDINEOFDaily` (VIIRS SNPP+NOAA-20, gap-filled, daily, ~4 km)
is updated to 2026-09-12. Kochi offshore read 3.29 mg/m³.
- *Finding:* the `pfeg.noaa.gov` host redirects to `coastwatch.noaa.gov`; use the latter.
- *Decision:* this is our chlorophyll source. Copernicus becomes an optional upgrade.

### Step 3 · Scaffold the project

Created the layout from CLAUDE.md (`src/marine/{sources,tools,risk,geo,agents}`,
`data/{static,snapshots,cache}`, `tests`, `scripts`, `docs`, `web`), ran `git init`, and
copied the five static GeoJSON files into `data/static/`.

Wrote:
- `pyproject.toml` — uv-managed, Python ≥ 3.11; httpx, pydantic, pydantic-settings,
  shapely, numpy, xarray, netCDF4, python-dotenv; dev: pytest, pytest-asyncio, ruff.
  Later added `truststore` (see Step 4).
- `.gitignore` (`.venv`, `data/cache/`, `.env`, node_modules), `.env.example` listing every
  key we might use — all optional, the system runs with none of them.
- `src/marine/config.py` — paths + `Settings` (pydantic-settings), including the 2 s
  `fetch_timeout_s` from rule 3.
- `src/marine/fixtures.py` — the five harbours from the brief plus `GULF_OF_MANNAR`
  (9.05 N, 79.10 E), ~15 km from the IMBL.

`uv sync --extra dev` — clean install.

### Step 4 · Snapshot fetcher, and three bugs it found

Wrote `scripts/snapshot.py`: async httpx, fans out per harbour, fetches Open-Meteo
marine + weather (7 days past + 8 forecast), VIIRS chlorophyll since 15 Aug, INCOIS Argo
latest, and the PFZ lines once globally. Saves each raw response under
`data/snapshots/<harbour>/<source>.json` and writes `manifest.json` with URL, HTTP
status, latency and `fetched_at` for every call. Failures are recorded, not raised.

First run: Open-Meteo and PFZ fine; Argo and chlorophyll failed. Diagnosis:
1. **INCOIS TLS** — `CERTIFICATE_VERIFY_FAILED` in Python although curl succeeded. The
   server sends an incomplete chain; certifi cannot complete it, the Windows trust store
   can. *Fix:* `truststore.inject_into_ssl()`. Added `truststore` to deps.
2. **NOAA 403** — httpx got `403 Forbidden` on the redirect target, curl did not. The
   server rejects the default `python-httpx` User-Agent. *Fix:* send a descriptive UA.
3. **INCOIS 400** — after the TLS fix, Tomcat returned 400 because httpx leaves `[ ]`
   literal in the URL while curl percent-encodes them. *Fix:* a `griddap()` helper that
   encodes brackets. Also corrected the Argo query to its real dimension layout
   (`TEMP[(last)][(5)][(lat)][(lon)]` — top level is 5 m, not 0).

Second run: every source green at all six points. Snapshot is 1.6 MB.

Windows note: the cp1252 console chokes on Unicode arrows in print output — run Python
with `PYTHONIOENCODING=utf-8`.

### Step 5 · Document and commit

Wrote `docs/data-sources.md` (the reference: exact URLs, schemas, units, gotchas, and the
IMD/Copernicus blockers) and committed everything as
`Phase 1: verify data sources, freeze static boundaries and a demo snapshot`.

**Phase 1 exit criterion met:** we can demo from `data/snapshots/` with the network off.

### Step 6 · Start this build log

Decided to keep this journal, updated with every step, so the whole timeline of the
project is readable in one place. `docs/data-sources.md` stays the *reference* (what the
endpoints are); this file is the *narrative* (what we did and why).

### State at end of Day 1

| Source | Status |
|---|---|
| Open-Meteo marine + weather | live, primary |
| INCOIS PFZ lines (GeoServer WFS) | live, only PFZ source |
| INCOIS sectors / landing centres, Marine Regions EEZ + IMBL | static, committed |
| NOAA VIIRS chlorophyll | live |
| INCOIS Argo | live but weak (1°, 6 weeks old) |
| IMD | **blocked — API key** |
| Copernicus | **blocked — account (optional)** |
| Bhashini | not yet tested (Phase 5) |

**Open actions for the team:** request an IMD API key; optionally register a Copernicus
Marine account.

**Next:** Phase 2 — `ledger.py` (`Observation`, `EvidenceLedger`), the source chain with
2 s timeouts and snapshot fallback, the typed tool belt, and the deterministic risk engine
with unit tests. Exit criterion: answer "is it safe off Kochi tomorrow" from a Python REPL
with a full ledger in under a second, no LLM involved.

---

## Day 1 (continued) — Phase 2 begins

### Step 7 · The evidence ledger (`src/marine/ledger.py`)

`Observation` exactly as CLAUDE.md specifies, plus three fields the rest of the system
needs: `provenance` (`live` / `cache` / `stale_cache` / `snapshot`), `latency_ms`, and an
`id` (`obs_0001`, …) that the ledger assigns so the verifier can match a citation to a
row. `EvidenceLedger` holds observations and — just as important — `MissingObservation`s:
every variable we tried to get and could not, with the reason. Helpers: `series()`,
`worst()` (the most adverse value in a window, which is what the risk engine wants),
`values()` (the set the verifier checks numeric claims against), `degraded()` and
`sources()` for the "this is cached data" banner.

### Step 8 · The source chain (`src/marine/sources/base.py`)

- *Decision:* every source is a `JsonSource` with two pure methods, `url(query)` and
  `parse(payload, query)`. Everything about *where the bytes came from* lives in the base
  class, so every source degrades identically.
- Two stages, kept deliberately separate: `try_live` (fresh disk cache within TTL, else
  network with the 2 s budget) and `try_fallback` (stale cache of any age, else the
  frozen snapshot). `SourceChain` runs stage one across *all* sources in priority order
  before stage two across any of them — rule 3 says "down the source chain, then to the
  snapshot", and a first draft that let each source reach for its own snapshot before the
  next live source was tried got this wrong. Fixed before it shipped.
- Confidence multipliers by provenance: live 1.0, cache 0.95, stale cache 0.7, snapshot
  0.5, times the source's own base confidence.
- Snapshot lookup picks the nearest snapshot point to the query and says so in the note
  ("kochi snapshot point, 12 km away"). If the snapshot does not cover the requested time
  window, `shift_window` moves to the same hours on the snapshot's last day and the note
  says that too. Loud degradation, never silent.
- Disk cache is `data/cache/<sha1(url)>.json` with `fetched_at`, so staleness is real.

Source modules written against the verified shapes: `open_meteo.py` (marine + weather,
unit conversions km/h→kt and m→km, grid-node offset → `distance_km`), `noaa_chl.py`
(VIIRS chlorophyll, trailing 30 days so one URL serves both baseline and latest),
`incois_erddap.py` (Argo 5 m temperature, base confidence 0.6), `incois_pfz.py` (global
daily fetch, parses Year + Julian day into an advisory date), `imd.py` (reports *why*
cyclone/lightning are missing; activates when a key arrives, but refuses to return data
from an unverified shape).

Live check at Kochi: marine 1.9 s first hit (TLS handshake), 13 ms from cache; weather
1.1 s / 13 ms; chlorophyll 2.6 s / 13 ms; PFZ 3.6 s / 66 ms. Forced offline (host
replaced with `offline.invalid`): 85 ms, 77 observations from the snapshot, confidence
0.5, note explaining it. A window 40 days out came back shifted and labelled.
- *Finding:* the PFZ fetch (1.1 MB) takes ~3.6 s live, over the 2 s budget. It is cached
  for 6 h, so the API must **pre-warm it at startup**. Noted for Phase 3.
- *Finding:* Argo at Kochi returns `null` (coastal cell). The source reports "empty" and
  the chain raises `SourceUnavailable`; it does not borrow a neighbouring cell. Chennai
  gets 29.38 °C from 51 km away, dated 30 July, confidence 0.6 — all visible in the row.

### Step 9 · Geo (`src/marine/geo/`)

`geodesy.py`: haversine, initial bearing, destination point, 16-point compass names, and
`LocalPlane` — an equirectangular projection centred on the query so shapely can do exact
nearest-point and line-crossing maths in kilometres.

`boundaries.py`: loads the Marine Regions lines, keeps only the ones that are a boundary
with another state (`Treaty`, `Median line`, `Court ruling` — 23 segments; "200 NM",
baselines and connection lines excluded). `position_status()` gives a three-way zone and
the nearest IMBL with distance, bearing and the closest point. `predict_crossing()`
projects the heading 12 h ahead, finds the first IMBL or EEZ-edge intersection, and flags
whether it falls inside the 90 min horizon — so the warning comes *before* the crossing.
- *Finding:* every harbour reported "not in the EEZ" because harbours are on land and
  the EEZ polygon starts at the coast. Tried INCOIS's India shapefile layer over WFS —
  **503**, the server was down (the snapshot argument, live). Found Marine Regions'
  `eez_land` union layer instead: one polygon for India + Andaman that classifies every
  test point correctly. Committed as `data/static/india_eez_land_union.geojson`.
- *Decision:* zones are `eez` (at sea, Indian), `land_or_port`, `outside_india`.
- Moved the `GULF_OF_MANNAR` fixture to (9.15 N, 79.40 E), 14.6 km from the Sri Lanka
  line, so an 8 kt boat heading east crosses in ~50 min — inside the horizon.

`pfz.py`: nearest PFZ lines to a point with distance, bearing, compass and the closest
point, capped at 300 km. Kochi: Kerala zone 42 km SW (228°). Veraval: empty list — the
honest answer for a sector with no advisory.

### Step 10 · The risk engine (`src/marine/risk/`) — 40 tests

`thresholds.py`: three vessel classes with separate tables; CLAUDE.md numbers for
traditional craft, progressively looser for motorised and mechanised. Every table is
stamped `CALIBRATION = "provisional"` and the verdict carries that string, so the UI can
say so until someone finds the INCOIS/IMD documents. Steepness bands (Hs/T²: 0.04
caution, 0.06 no-go) were chosen so that 1.4 m at 5 s is flagged as chop while 1.4 m at
10 s is not.

`rules.py`: `evaluate(RiskInputs, VesselClass) → RiskVerdict`. Seven parameters — wave
height, wind (gusts escalate), steepness, visibility, lightning, cyclone, boundary — each
returning its own `ParameterVerdict` with value, thresholds, reason and the ledger ids
that produced it. Then `max()` over levels. **Worst-of wins; there is no averaging code
path to get wrong.**
- *Decision:* a missing wave-height or wind value makes the status `insufficient_data`
  and floors the level at CAUTION. The engine can never say GO without both.
- *Decision:* with no lightning feed (IMD key missing), Open-Meteo thunderstorm codes and
  CAPE ≥ 2000 J/kg act as a *convective proxy* — status `proxy`, never labelled lightning,
  and the gap is still listed. The CLAUDE.md "thunderhead over calm seas" case is a test.
- *Decision:* a predicted boundary crossing inside the horizon, or a position already
  outside Indian waters, is NO_GO. Detention is not a lesser outcome than a swamping.

`tests/test_risk.py` (40) and `tests/test_geo.py` (27): all pass. Engine ≈ 0.1 ms.

### Step 11 · The tool belt (`src/marine/tools/`) — 14 tests

Fifteen typed functions, Pydantic at every boundary, all writing into one per-request
`ToolContext.ledger`:

| Tool | Does |
|---|---|
| `resolve_location` | name → coordinates + INCOIS sector, from the 5 test harbours, 16 curated major ports, and INCOIS's 1223 landing centres; exact, alias, then guarded fuzzy |
| `get_wave_forecast` / `get_wind_forecast` / `get_visibility_forecast` / `get_sea_state` | windowed series through the chains |
| `get_chlorophyll` / `get_argo_temperature` | trailing 30-day VIIRS chl; Argo 5 m cross-check |
| `get_pfz_advisory` | nearest INCOIS PFZ lines with our bearing/distance, as ledger rows |
| `check_position` / `predict_boundary_crossing` | zone + nearest IMBL; projected crossing |
| `assess_sailing_risk` | worst-of over the ledger window → `risk.rules.evaluate` |
| `safety_briefing` | the composite: `fan_out` (4 fetches concurrently) then the verdict |
| `cyclone_status` / `lightning_status` | record the IMD gap in the ledger |
| `named_window` | "tomorrow morning" → IST 05:00–12:00 → UTC, deterministic |

- *Decision:* `safety_briefing` exists so the common question costs one tool call and one
  parallel fan-out, not four sequential LLM round-trips. The planner can still call the
  pieces individually for unusual questions.
- *Decision:* geometry results (PFZ distance, IMBL distance, minutes to crossing) are
  written to the ledger as observations too, so "42 km SW" is citable like any number.
- *Finding:* "Kochi" resolved to the same-named INCOIS landing centre instead of the test
  harbour. Fixed ordering so harbours win a name clash.
- *Finding:* "Rameswaram" fuzzy-matched to "Kameshwaram" and "Kasimedu" to
  "Kottaimedu" — neither real port is in INCOIS's landing-centre layer. Added a curated
  `KNOWN_PORTS` list (Rameswaram, Kasimedu, Malpe, Vizag, Sassoon Dock, …), an alias table
  (Cochin, Madras, Bombay, Vizag, Paradeep, …), and a first-three-letters guard on fuzzy
  matches. Unknown names return `None`, never a guess.
- *Finding:* a fresh cache hit was being reported as "degraded". Now only stale cache and
  snapshot count.
- *Finding:* wind and visibility tools hit the same weather URL; under `asyncio.gather`
  both fired. Added in-flight request de-duplication in `try_live` — one network call,
  both callers await it. Test pins it at 2 requests per briefing, not 4.

`tests/test_tools.py` stubs the network with `httpx.MockTransport`: an `offline` fixture
where every request raises (the chain must answer from the committed snapshot and label
it), and a `live_from_snapshot` fixture that serves snapshot payloads as 200s. No test
touches the internet. 14 tests, including "heading east from the Gulf of Mannar is NO_GO
whatever the sea state".

### Step 12 · Phase 2 exit criterion — met

`scripts/ask.py`: the REPL answer with no LLM anywhere.

```
$ uv run python scripts/ask.py kochi
=== GO === for a traditional craft off Kochi, Wed 16 Sep 05:00–12:00 IST
status: verdict   engine: 0.12 ms   fetch+risk: 368 ms   total: 389 ms
  wave_height  GO   wave_height 1.02 m within limits  [obs_0077]
  wind         GO   wind 5.9 kt within limits         [obs_0013]
  ...
  cyclone      —    missing  no cyclone feed (IMD key missing)
PFZ: advisory 2026-09-14 — #1 KERALA 42.1 km SW (228°)
ledger: 128 observations, 2 missing
```

Cold (network): ≈ 2.2 s. **Warm cache: 389–448 ms, full ledger** — under the one-second
target. Engine itself: ≈ 0.1 ms.

Gulf of Mannar, heading 090 at 8 kt: **DO NOT SAIL — current heading crosses
Sri Lanka - India in 59.3 min**, with the sea itself benign. The predictive geofence
works as a safety parameter, not an afterthought. Open-Meteo returned a 503 during that
run; the chain absorbed it.

All five harbours answered (Veraval: CAUTION on visibility 4.72 km and honestly "no PFZ
near this point"; Chennai / Paradip / Port Blair: CAUTION on the CAPE proxy).

**Open calibration item:** the CAPE ≥ 2000 J/kg convective proxy fired at three Bay of
Bengal harbours on an ordinary September day (2230–3540 J/kg). During the monsoon that
may be every day, and a warning that fires every day is ignored. Needs a real lightning
feed (IMD key) or a climatology-aware threshold; parked, not tuned blind.

Test count: 81 (risk 40, geo 27, tools 14). All green. Committed.

**Next:** Phase 3 — the planner (the only free-form LLM step, emitting a typed task DAG
over these tool names), the four specialists, the LangGraph state machine, and the
synthesis + verifier pass that strips any number not in the ledger.

### Step 13 · GitHub

Renamed the branch `master` → `main`, wrote `README.md` (principles, status table, quick
start, sources, layout), and pushed the six commits to the private repo
`github.com/harshvsinghnorth/sagar-setu`. `gh` is not installed on this machine, so the
repo was created on github.com by hand and pushed over HTTPS with the credentials already
in Windows Git Credential Manager. From here every phase ends with a push.

---

## Day 2 — 2026-09-16

### Step 14 · Budget reality check → model-agnostic LLM layer

Before Phase 3, the cost of the LLM layer came up. It is the **only** paid component in
the design (every data source, the map library, hosting and GitHub are free), and it
should have been called out on Day 0. The user has no budget, so the plan changed:

- *Decision:* the LLM sits behind a thin provider interface (`agents/llm.py`, selected by
  `LLM_PROVIDER` in `.env`). Develop and demo on a **free tier**; Anthropic / Ollama are
  optional alternatives. This is also the better story: the intelligence is in the
  architecture, not the vendor.
- *Finding:* Google's Gemini API free tier works from this machine with no card.
  `gemini-2.5-flash` and older are gone for new keys; the API itself points to
  `gemini-3.6-flash`. Verified live: a Tamil question ("நாளை காலை கடலுக்கு போகலாமா?") came
  back correctly identified, translated, and answered in Tamil, as JSON. **2.6 s with
  reasoning off** (`thinkingBudget: 0`), 4.3 s with default reasoning. `gemini-3.8-flash`
  timed out at 45 s; `3.5-flash-lite` rejects the thinking-off flag. So: `gemini-3.6-flash`,
  thinking off for the planner, streaming for synthesis.
- *Finding:* 2.6 s is above the 600 ms planner budget in CLAUDE.md. Mitigations planned:
  a deterministic fast path for the common question shapes (location + day-part + safety
  → no LLM call needed for the plan), and streaming so the first token of the explanation
  lands early. The budget is a target for the demo, not a reason to pay for a faster model.
- *Incident, caught:* the key was pasted into `.env.example` — a **tracked** file — instead
  of `.env`. It was not yet committed. Moved to `.env` (gitignored, verified), template
  restored. Lesson recorded: say "create a new file called `.env`" explicitly, and check
  `git status` before every commit for anything that looks like a credential.

**Still worth getting, none blocking:** IMD API key (cyclone + lightning parameters go
live), Copernicus account (forecast chlorophyll, better currents), Bhashini keys
(government translation for the language round trip; Gemini is the fallback), and
INCOIS's official small-craft thresholds document (calibration).

### Step 15 · Copernicus Marine verified

Registered a free account (Academic; blue markets: Extremes/Hazards/Safety, Education).
`copernicusmarine` toolbox 2.4.1 installed; login works with username + password from
`.env`. Opened `cmems_mod_glo_bgc-pft_anfc_0.25deg_P1D-m` (chlorophyll, daily, 0.25°) at
Kochi offshore:
- *Finding:* time axis runs **2021-11-01 → 2026-09-25** — a 9-day forecast *and* a
  five-year daily baseline in one dataset. That is exactly what the Analytics & Causal
  agent needs for "is this week's chlorophyll unusual?". NOAA VIIRS stays as the
  no-account fallback behind it in the chain.
- *Finding:* opening the dataset takes ~11 s (lazy remote zarr). Far outside the 2 s
  budget, so Copernicus is **pre-fetched per harbour by a background job** into
  `data/cache/` (and the snapshot), never fetched inside a request. Wiring deferred to
  the Analytics work in Phase 3; the source module will read the cache only.
- Latest values near Kochi: ~1.0–1.1 mg/m³ (VIIRS gave 3.3–4.3 at the coast — different
  grid, different product; the ledger will show both with their distances, and the Ocean
  agent's job is to flag the disagreement, not average it).

**Still open (user working on them):** IMD key (needs a letter from the college — the
form at api.imd.gov.in/public/profile.php is free; questionnaire answers drafted),
Bhashini keys, INCOIS threshold document.

### Step 16 · Phase 3 — the LLM layer, planner, specialists, graph, verifier

**`agents/llm.py` — one interface, four providers.** `complete()` and `stream()`
behind a Protocol; `GeminiLLM` (REST, no SDK; `thinkingBudget: 0` for speed), `OllamaLLM`
(local, offline), `AnthropicLLM` (optional, paid, SDK loaded lazily), and `NoLLM`, which
raises `LLMUnavailable` so every caller has a deterministic fallback. Structured output is
done the portable way — JSON schema in the prompt, pydantic validation on the way out, one
corrective retry — so it behaves identically on every provider. `LLM_PROVIDER=auto` picks
Gemini if a key exists, else Anthropic, else none.

**`agents/planner.py` — the only free-form LLM step, and mostly not an LLM.**
- *Decision:* a **deterministic fast path** handles Latin-script questions in the common
  shapes with no model call: intent by keyword, location by scanning 1–3-word spans
  against the resolver, day/part words, vessel words or "9 m", heading and speed by
  regex. ~50 ms. Every English demo question takes this path, which is how we stay inside
  the 600 ms planner budget on a free tier whose round-trip is ~2.8 s.
- The LLM path (Indic scripts, vague phrasing) does language detection, translation and
  intent extraction in **one** JSON call. Verified live: Tamil → Kochi/safety; Hindi with
  "my boat is 15 metres" → Veraval/motorised (it applied the vessel-class rule itself);
  "write me a poem" → off_topic; "what does a 2 m swell mean" → general_knowledge with a
  short answer; "is it safe tomorrow" → clarify, asking for the harbour in the user's
  language.
- Eight intents: safety, pfz, boundary, conditions, chlorophyll, general_knowledge,
  off_topic, clarify. The task DAG is derived from the intent by `tasks_for` — typed and
  explicit, so parallelism is a property of the plan, not of prompt luck.
- *Finding:* the fast path first mis-filed "what does a 2 metre swell mean" as
  `conditions` → clarify. Fixed: a data intent with no location defers to the model,
  which knows the difference between "explain" and "fetch".
- *Finding:* one planner call took 17 s (free-tier hiccup); the same query then took
  2.9 s twice. Transient; timeout stays 20 s.

**`agents/specialists.py` — three of the four are plain Python.** Ocean & Weather fans
out via the tool belt and summarises worst-of per variable, with a disagreement hook that
names sources rather than averaging them (ready for Copernicus SST/currents). Geospatial
& Boundary does PFZ + position + predictive crossing. Analytics & Causal compares the
latest chlorophyll with a trailing 30-day baseline (z-score, 7-day trend) and names a
*mechanism as a hypothesis* — "consistent with upwelling", "one possible contributor" —
never a cause.

**`graph.py` — LangGraph.** `planner → {ocean_weather, geospatial, analytics} → risk →
synthesis`, with a direct edge to synthesis for clarify / off-topic / knowledge. The
conditional edge returns the list of specialist nodes the DAG needs; they run in the same
superstep, so concurrently. Every node appends a timed event — the API will stream these
as agent progress. A specialist that throws degrades the answer; it never kills it.

**`agents/synthesis.py` — Synthesis & Verify.** `build_brief` packs everything into one
deterministic brief that is *the model's entire world*; the same brief renders the
template answer used with no model. The prompt's rules: verdict first and final; only
numbers from the brief; degradation and gaps must be stated; the user's language; plain
spoken register. `verify()` then scans the draft: every number (Latin or Indic digits)
must match a ledger value, a threshold, a window hour or a count the brief states; dates
and clock times are stripped first. An unsupported number → one corrective retry → else
the template ships. English drafts are also checked for phrases that contradict a DO NOT
SAIL. The verdict badge and the degradation banner in the UI will come from the engine
and the ledger, never from the prose, so prose cannot soften them.
- *Finding:* the verifier flagged dates ("17 Sep", "2026-09-15") as unsupported numbers.
  Fixed by stripping date/time patterns before the scan.
- *Finding:* the model called a fresh cache hit "cached weather data" because the word
  `cache` appeared in the evidence bracket. Fixed: the brief labels provenance as
  `current` / `OLDER CACHED DATA` / `STORED SNAPSHOT`; a fresh cache is current.
- *Decision:* boundary crossing inside the 90 min horizon stays NO_GO; **inside twice the
  horizon is now CAUTION** ("change heading before then"). Trigger: Rameswaram heading 090
  at 8 kt reaches the Sri Lanka line in 94.5 min — a GO by the letter of the horizon, and
  obviously not what a fisherman needs to hear. Test added.
- *Decision:* PFZ search capped at 150 km (was 300). Veraval was being told about
  Maharashtra's zones 237 km away; "no advisory near you today" is the honest answer.

**Tooling finding:** the Bash tool collapses backslash pairs before the shell sees them,
so every `\b` in a regex pushed through a heredoc arrived as a **backspace byte**. Cost an
hour across two files. Rule from now on: code containing backslashes goes through the
Write/Edit tools, never a shell heredoc. A one-off script strips stray `\x08` bytes.

**Phase 3 exit criterion — met.** `scripts/chat.py`:

| Query | Path | Result | Total |
|---|---|---|---|
| "Is it safe to go out from Kochi tomorrow morning?" | fast path | CAUTION (visibility 4.78 km); 10 numbers, all verified | 3.6 s |
| Tamil, Rameswaram, heading 90 at 8 kt, 9 m boat | LLM | CAUTION; crossing in 94.5 min flagged; answer in Tamil, 13 numbers verified | ~8 s |
| Hindi, Veraval, 15 m boat | LLM | CAUTION; answer in Hindi, motorised thresholds, 8 numbers verified | 8.4 s |

Where the time goes on a non-English question: planner ~2.8 s + synthesis ~2.5 s (both
the free model) + live fetch 1.5–2.5 s. English questions skip the planner call. The
2.4 s first-token budget in CLAUDE.md is not met on the free tier for Indic queries;
mitigations for Phase 4: pre-warm the demo harbours' caches in the background (fetch
→ ~30 ms), stream the answer so the first token lands at ~4 s, and show agent progress
events so the wait is legible. Paying for a faster model is not on the table.

`tests/test_agents.py` (22): fast-path intents, DAG shape, verifier (roundings, Indic
digits, dates, contradiction), and the graph end to end with a scripted fake model —
including one that invents "waves 4.7 m, wind 41 kt" and is caught and retried. Total
suite: 104 tests, no network, no model.

**Next:** Phase 4 — `api.py` (FastAPI + SSE streaming of events and answer chunks),
then the React + MapLibre interface: chat, map with PFZ lines / EEZ / IMBL / vessel
position / projected track, and the evidence ledger panel with staleness shown.

---

## Day 3 — 2026-09-18

### Step 17 · Dataset dossier for the project review

Paused Phase 4 to prepare for a review with the supervising professor, whose focus is on
the datasets. Deliverables, all under `docs/`:

- `docs/datasets.md` — the dossier: the idea in one paragraph, the data principle
  (evidence ledger), a catalogue of ten datasets, a card per dataset (publisher, what we
  take, resolution, cadence, access, limits, sample file), a section on datasets
  **evaluated and rejected** with reasons, the data-flow diagram, and three open questions
  to put to the professor (threshold calibration source, coastal chlorophyll product
  choice, IMD access).
- `docs/datasets/*.csv` — 15 extracts of real responses via `scripts/export_datasets.py`:
  Open-Meteo hourly marine + weather for six points (2,160 rows each), the 87 PFZ lines and
  their 42,740 vertices, 1,223 landing centres, 14 sectors, 32 boundary features, VIIRS
  and Argo samples, the fetch manifest, and — pulled live — Copernicus chlorophyll for
  six points (1 Jul → 27 Sep 2026) plus the **five-year daily record at Kochi (1,792
  values)**.
- `docs/datasets/Sagar_Setu_Datasets.xlsx` — 16 sheets: a catalogue plus one sheet per
  extract (`scripts/build_dataset_workbook.py`). No formulas, so it opens identically
  anywhere.
- Two figures (`scripts/plot_datasets.py`): all datasets on one map, and five years of
  chlorophyll off Kochi with the VIIRS coastal pixel overlaid.

- *Finding, from the figure:* the south-west-monsoon upwelling bloom off Kochi recurs
  every June–September in the Copernicus record, and **the 2026 bloom is visibly weaker
  than 2022, 2024 and 2025**. That is the "productivity decline" causal query showing up
  in the data unprompted. Recorded as an observation to test properly in the Analytics
  work, not as a claim.
- *Finding:* VIIRS at the Kochi coastal pixel reads 3–11 mg/m³ while the Copernicus 0.25°
  mean reads ~1 — a 4 km coastal pixel and a 28 km offshore box measure different water.
  The dossier says so and the Ocean agent's disagreement rule (show both, never average)
  now has a concrete case behind it. Raised as a question for the professor.

---

## Day 4 — 2026-09-21/22

### Step 18 · AI practice assignment (side task)

Answered the course's AI practice assignment around Sagar Setu
(`docs/AI_Practice_Assignment_Sagar_Setu.docx`): PEAS table and agent classification
(model-based, goal-based, knowledge-based core — deliberately not utility-based), search
problems in the project, KRR, explainability; plus an A* case study run for real
(`scripts/assignment_q2_astar.py` — admissibility and consistency checked, A* vs UCS vs
greedy; greedy is lured into the S4 trap exactly as the question hints), a CSP
formulation, medical-agent architectures, and Rock-Paper-Scissors.

### Step 19 · Phase 4 — API and interface

**`src/marine/api.py` — FastAPI + SSE.** `POST /ask` streams `agent` events as each node
finishes, `chunk` events as the answer is written, then one `result` with everything the
interface renders (verdict, ledger, degradation, PFZ and boundary geometry, projected
track), then `done`. `GET /geo/static` serves the EEZ outline and IMBL lines simplified to
~1 km (228 KB instead of 3 MB). On startup a background task pre-warms the PFZ advisory
and the five harbours' forecasts so the first demo question is warm.
- The graph got `ask_streaming()` (LangGraph `astream` with `stream_mode="updates"`) so
  node events reach the client before the answer exists, and request-level `overrides`
  (vessel class from the UI selector; GPS position/heading/speed if a device supplies
  them) that fill gaps the question left.

**`web/` — React + Vite + TypeScript + MapLibre.** Free OSM raster tiles, no token.
- Chat column: streamed answer, agent trace with per-node timings, the **verdict badge
  rendered from the engine's result, never parsed from the prose**, reasons, all seven
  parameters with evidence ids, a degradation banner driven by the ledger, vessel-class
  selector (persisted — the brief's "ask once at onboarding").
- Map: EEZ, IMBL (dashed), harbours, PFZ lines with rank/distance/compass labels, bearing
  lines from the harbour to each zone, the projected track and the predicted crossing
  point. Labels are HTML markers rather than symbol layers so no glyph server is needed —
  one less network dependency in a demo.
- Evidence ledger panel: every row with id, value, valid-for time (IST), a **freshness
  chip** (green < 15 min, amber < 2 h, red older / snapshot), source, grid distance and a
  confidence bar; rows the verdict cited are highlighted and listed first; missing
  variables listed with their reason. `show all` expands to the full hourly series.

**Bugs the interface exposed** (all fixed, all with tests):
- *Rule-1 bug:* for a boundary question — no verdict computed — the model's answer began
  "GO." because the prompt said "state the verdict first". Two fixes: a heading question is
  a safety question, so the DAG now runs the ocean fetch and the engine for `boundary`
  intent (Rameswaram heading 090 → CAUTION, "change heading before then"); and the
  verifier rejects verdict words (GO / CAUTION / DO NOT SAIL / safe / unsafe) whenever the
  brief has no verdict. Uppercase-only for the tokens so "go 42 km south-west" still passes.
- *Streaming showed a rejected draft:* the first draft streams to the screen before the
  verifier rejects it. Added a `RESET` sentinel → `reset` SSE event → the UI clears the
  draft before the retry (or the template) streams in.
- *Indic place names:* the Tamil demo question came back from the model as
  `இராமேஸ்வரத்தில்` (Tamil script, locative suffix) instead of "Rameswaram"; the resolver
  could not match it and the system asked "which harbour?". Fixed with a deterministic
  `INDIC_STEMS` table (Tamil / Hindi / Malayalam stems for the known harbours, suffix-
  insensitive) plus a firmer planner instruction. The demo no longer depends on the model
  transliterating correctly.
- *NOAA VIIRS timing out:* it takes 1–3 s, so under the 2 s budget it fell to the snapshot
  on most requests and the banner said "not current". Added a per-source `timeout_s`;
  chlorophyll is not a safety input, so it gets 6 s. Safety inputs keep 2 s.
- CSS: the ledger table forced horizontal page scroll; grid tracks now `minmax(0, 1fr)`.

**Tooling:** the Bash tool's backslash collapse struck again twice (`\b` → backspace,
`\x00` → NUL byte in source). Both caught by tests; both fixed with a byte-level script.
Rule stands: regex and escape sequences go through Write/Edit only.

**Verified in the browser** (Vite dev server + uvicorn `--reload`):
- English Kochi safety question: fast path, CAUTION, verified, 6.2 s.
- English Rameswaram heading 090 at 8 kt: CAUTION with steepness, convective proxy and
  the 94.5 min crossing; track and crossing marker on the map.
- PFZ question at Paradip: "no PFZ advisory near Paradip today" (true for the 21 Sep
  advisory), chlorophyll anomaly z = 1.52 shown; the model's first draft was rejected and
  the retry took 29 s — free-tier variance, hidden by the reset event but noted.
- **Tamil Rameswaram heading question through the UI: CAUTION badge, Tamil answer with
  every number verified, track + crossing on the map, ledger with cited rows first.
  7.9 s.** All five demo items from the brief on one screen.

Suite: 111 tests. Next: Phase 5 — Bhashini when keys arrive (Gemini covers the round
trip today), then the stretch items the user asked for (multi-turn, A* route suggestion,
spoken input), then Phase 6 hardening and the offline rehearsal.

### Step 20 · Evaluation: "how often are we right?"

The professor asked for an accuracy figure — if the system says "do not go out tomorrow",
how often is it right, because a false alarm wastes a fisherman's day. We had no number,
and said so. Then built the harness.

- *Decision:* report a **contingency table, not one accuracy number**, because the two
  errors are not equal: a miss (said go, was rough) is the dangerous one; a false alarm
  (said don't go, was fine) is the wasted day. Hit rate (POD) and false-alarm ratio (FAR)
  are reported separately, plus CSI, accuracy, the full 3×3 confusion matrix, and the
  wave-height error (MAE / RMSE / bias).
- *Finding:* Open-Meteo exposes **the forecast as it was issued 1, 2 and 3 days earlier**
  for every hour (`wave_height_previous_dayN` on the marine API; the previous-runs API for
  wind and gusts), 92 days back. That is exactly the data a backtest needs: the verdict a
  fisherman would have seen the evening before versus the model's final analysis of the
  morning. Visibility has no previous-run archive, so it is held neutral for both series.
- *Finding:* no INCOIS / NIOT buoy or wave-rider feed is publicly reachable (ERDDAP has
  no table datasets beyond Argo; the WRB pages 404). So the truth in this evaluation is
  the model's own analysis, **not the sea** — stated in the report's first paragraph, and
  the numbers are called an upper bound on skill. The harness runs unchanged against buoy
  data if any is obtained (question for the professor).

`src/marine/eval/backtest.py` builds, for every harbour-morning (05:00–12:00 IST) and
each lead, the worst-of inputs from both series, runs the same engine on both, and scores.
`scripts/eval_report.py` writes `docs/evaluation.md`. Results, 92 mornings (22 Jun →
21 Sep 2026, peak south-west monsoon) × 5 harbours = 460 harbour-mornings, traditional
craft:

| lead | DO-NOT-SAIL hit rate / FAR | CAUTION-or-worse hit rate / FAR | 3-way agreement | Hs MAE |
|---|---|---|---|---|
| 1 day | **93.9% / 3.1%** (31 of 33 rough mornings warned; 1 false alarm in 32 warnings) | 90.7% / 3.4% | 93.5% | 0.056 m |
| 2 days | 97.0% / 17.9% | 86.6% / 4.1% | 90.2% | 0.101 m |
| 3 days | 90.9% / 30.2% | 85.2% / 10.2% | 85.0% | 0.121 m |

The two day-ahead misses were graded CAUTION, never GO — the worst-of rule behaving as
designed. Veraval (Gujarat, SW monsoon) is the stress test: a do-not-sail morning one day
in three, hit rate 96%, zero false alarms. Chennai and Port Blair had no do-not-sail
mornings in the period (the Bay's rough season is Oct–Dec). Skill falls with lead mostly
through false alarms — so the interface should treat the day-ahead verdict as the decision
and longer leads as outlook.

**Prospective log started** (`scripts/daily_log.py --log` / `--verify`): each evening the
verdict for the next morning is recorded at all five harbours; the next afternoon the
outcome is scored. These are predictions made before the fact — the strongest evidence a
reviewer can be given — and they accumulate into `docs/evaluation.md` automatically.
First entries 22 Sep: Kochi GO, Chennai GO, Veraval CAUTION (convective proxy), Port Blair
CAUTION (visibility 2.58 km), **Paradip DO NOT SAIL (2.84 m)**. Scheduling instructions
(Windows `schtasks`) are in the script's docstring — the user runs those; I did not
create scheduled tasks on their machine.

Tests: `tests/test_eval.py` pins the contingency arithmetic and the miss / false-alarm
separation. Suite: 115.

**Needs from the user:** ask the professor / department for INCOIS or NIOT buoy data;
run the two `schtasks` commands so the log grows without anyone remembering.

### Step 21 · Architecture submission

A course assignment asked for the project's main proposed architecture, showing the major
components and their interactions. Produced three artefacts, all generated from the real
module layout rather than sketched:

- `scripts/plot_architecture.py` → `docs/architecture/architecture.png` — an eight-layer
  component diagram (client · API · orchestration · decision · tools · geo · data access ·
  sources) with the evidence ledger drawn as a cross-cutting right rail, the LLM provider
  layer and the evaluation harness as side boxes, and **the load-bearing line drawn
  explicitly**: a dashed red rule across the figure separating "models plan and explain"
  above from "ordinary Python fetches and decides" below. Request path downward, result
  path upward, ledger writes as dotted arrows, plus a tool-call lane showing that all data
  access funnels through the tool belt.
- `docs/architecture/request_flow_detailed.png` — the eight steps of one Tamil question with
  measured timings and a per-step badge marking model vs code vs "code · no model".
- `docs/architecture.md` and `docs/Sagar_Setu_Architecture.docx` (2 300 words, 8 tables,
  both figures embedded) — component catalogue per layer, the interaction narrative, the
  `Observation` schema, key design decisions with the alternatives rejected, and the
  non-functional properties.

- *Finding:* DejaVu Sans has no Tamil glyphs, so the Tamil example question rendered as
  boxes. Windows ships Nirmala UI, which covers Tamil and Devanagari; the script now
  locates it via `font_manager` and uses it for Indic strings, falling back silently.
- *Finding:* drawing the diagram surfaced a genuine layout problem in my own first attempt —
  an arrow from the tool belt to the data-access layer ran straight through the
  `geodesy.py` box, and the specialist→tools arrows crossed the risk-engine box. Both were
  rerouted (a lane at x = 67.5 for tool calls, a gap between the geo boxes). Worth noting
  because the exercise of drawing the real dependencies is what exposed them.
- Layout was iterated against the rendered PNG four times — overlapping labels, text
  overflowing boxes, and a heading colliding with a flow lane were each fixed by reading
  the image, not by guessing.

### Step 22 · Rewriting the architecture submission for a non-technical reader

Feedback on Step 21: *"This document needs to be simple. So that it is easy for professor
to understand. Don't make such complex diagrams that nobody will understand or read."*

Fair, and worth recording as a lesson rather than just a fix. The Step 21 diagram was
accurate — eight layers, every module named, real dependency arrows — and that is exactly
what made it unreadable. It was a diagram for someone who already knew the system. The
submission needs a diagram for someone deciding whether the system is sensible.

What changed:

- New `scripts/plot_architecture_simple.py` → `docs/architecture/architecture.png` and
  `flow.png`. Five numbered steps down the page instead of eight layers: understand the
  question → collect the data → decide if it is safe → write the answer → check every
  number. Each box carries an **AI** or **NO AI** badge, so the one thing the reader must
  take away — that no model decides safety — is visible without reading a word of prose.
  The red dashed line survived the redraw, relabelled in plain English: *"Below this line
  there is no AI — only fixed rules."* The evidence ledger stays as a right-hand rail,
  with one solid arrow in and three dotted arrows out.
- The Step 21 figures are kept as `architecture_detailed.png` and
  `request_flow_detailed.png` — still correct, still in the repo, now the appendix rather
  than the submission.
- `docs/architecture.md` cut from 2 300 words and 8 tables to ~900 words and 2 tables; the
  long version preserved verbatim as `docs/architecture-detailed.md` and linked from the
  top of the short one. `docs/Sagar_Setu_Architecture.docx` rebuilt from the same text:
  7 short sections, both simple figures, 0.33 MB (was 0.90 MB).
- Vocabulary pass over the whole document. "Orchestration layer" → "the server".
  "Deterministic risk engine" → "safety rules (no AI)". "Specialist agents fan out in a
  single superstep" → "three collectors run at the same time, not one after another".
  Nothing was softened or made vaguer — the claims are identical, the words are shorter.

- *Finding:* the simple figure needed two rounds of overlap fixes of its own, read back
  off the rendered PNG each time. Titles were overlapping their subtitles (fixed by
  anchoring the title with `va="top"` near the box top and the subtitle at a fixed offset
  below, instead of centring both); the AI badges collided with the titles (moved outside
  the box, to its left); the red line ran through the ledger text (line shortened to stop
  before the rail); and the last line of three subtitles spilled below their boxes (box
  heights now derived from the line count: 7.5 / 9.5 / 12.0).
- *Finding worth keeping:* every diagram in this project has now been debugged by reading
  the rendered image back, never by trusting the layout code. Four iterations on the
  detailed figure, two on the simple one. Matplotlib will happily draw text outside a box.

- *Follow-up:* still too busy. Stripped it again — the question and answer became plain
  captions rather than boxes, the separate "Data sources" box folded into one line inside
  step 2, and the evidence ledger's six lines of explanation cut to two. Five boxes, one
  or two short lines each, one red line. Rule adopted for this figure: anything needing a
  third line of text belongs in the document, not the picture. 0.24 MB, down from 0.90.


### Step 23 · Mid-term review: literature, research gap, synopsis and deck

A mid-term presentation (13 Oct 2026) marked on four criteria: comprehensiveness of the
literature review (10), research gap (5), objective / problem definition (5), proposed
methodology including tools and dataset (5). Fifteen of the twenty-five visible marks sit
in literature and gap — the two things the project had never written down.

- `docs/synopsis.md` → `docs/Sagar_Setu_Synopsis.docx`, ~3,500 words: abstract, problem
  definition, six numbered objectives, an eleven-part literature review, six enumerated
  research gaps, methodology, the backtest results, remaining work and 15 references.
- `docs/Sagar_Setu_MidTerm.pptx`, 10 slides, built by `scripts/build_midterm_deck.js`
  (pptxgenjs, themed, with speaker notes on every slide).

**Every reference was verified against its source** rather than recalled — author lists,
venues, volumes and page numbers fetched from the publisher or repository record. Three
candidate citations were dropped because they could not be confirmed to exist. A fabricated
citation in an academic submission would be worse than a thin bibliography.

- *Finding — the calibration target exists, and we had missed it.* INCOIS publishes
  **Small Vessel Advisory and Forecast Services (SVAS)**, an impact-based advisory giving a
  **Boat Safety Index** for potential vessel-overturning zones ten days ahead. It is
  computed from significant wave height, wave steepness, directional spread and rapid
  wind-sea development, and issued per **beam-width** class (< 4 m, 6 m, 7 m). Three
  consequences: (1) it independently confirms that steepness belongs in our table; (2) we
  are missing directional spread entirely — Open-Meteo does not expose it, Copernicus does;
  (3) our vessel classes key on *length*, but INCOIS keys on *beam*, which is the better
  discriminator for capsizing. Recorded in `src/marine/risk/thresholds.py`. SVAS still
  publishes no numeric thresholds, so `CALIBRATION` stays provisional.
- *Finding:* the closest architectural relative in the literature is ClimSight's XCLIM-AI
  extension, which reports its largest gains in actionability when climate indicators are
  **computed deterministically rather than generated**. That is independent, published
  support for this project's central constraint, arrived at separately.
- *Finding:* no LibreOffice on this machine, so the skill's PDF-render QA path fails.
  PowerPoint COM automation (`$ppt.Presentations.Open(...).Export(dir,"PNG")`) renders with
  the real fonts, which is strictly better QA than LibreOffice substitution. Two defects
  were found that way and fixed: misaligned label/description baselines on the status slide
  (text boxes of differing heights both vertically centring their content), and loose
  vertical gaps on three slides.
- Deck validated clean by the skill's `validate.py`; all ten slides inspected as rendered
  images.

**Needs from the user:** the three asks are now on the closing slide — IMD API key
(institutional letter), INCOIS's numeric small-craft criteria behind the Boat Safety Index,
and INCOIS/NIOT buoy observations to replace model analysis as evaluation truth.

### Step 24 · Presentation script

Spoken script for the 13 Oct mid-term review, generated in two formats from one source so
they cannot drift: `scripts/build_script_doc.js` writes both `docs/presentation-script.md`
and `docs/Sagar_Setu_Presentation_Script.docx`.

Contents: a pre-flight checklist, the four things to land, a slide-by-slide script with
per-slide timings, stage directions and scripted bridge lines, a timing table with explicit
instructions on what to cut if the slot shrinks to eight minutes, twelve anticipated
questions with answers, the three asks, a map of the synopsis, and a table of figures to
know cold.

- Measured 1,559 spoken words — 10.4 to 12.5 minutes depending on pace, against a stated
  13:15 that allows for pauses. The timing claim is checked, not guessed
  (`scratchpad/count_speech.py`).
- The Q&A section answers the uncomfortable questions rather than avoiding them: why not
  let the model decide; is this just an API wrapper; how do you know 93.9 % is real when
  you have no buoy data; and why an ISRO/INCOIS project leans on a European data source.
  That last one is the weakest point in the project's story and the script says so plainly.
- *Note:* the Bash backslash-collapsing problem bit again while counting words with an
  inline regex. Confirms the standing rule — anything containing backslashes goes through
  Write to a file, never a shell heredoc.

### Step 25 · Deck rebuilt around the marking scheme; a citation corrected

Feedback: the Step 23 deck "doesn't cover what we want to cover properly". Correct. It was
a pitch deck — story-led, stat callouts — for a review marked on literature (10), gap (5),
problem/objectives (5) and methodology (5). It gave the 10-mark literature criterion two
narrative slides with no study-by-study survey, put the six gaps only in the synopsis, and
had **no dataset slide** for a supervisor whose focus is datasets.

Rebuilt (`scripts/build_midterm_deck.js`) as 10 slides + references:
problem definition → **three literature-survey tables** (study · contribution · method/data
· finding · *limitation for our problem*) → comparison matrix → **gap → evidence →
objective** table (G1–G6 → O1–O6) → methodology I (steps, technique, AI or not, with the
architecture figure) → **methodology II: dataset table** (9 sources, status incl. the two
that fail) → evaluation and status → references. The red "limitation" column on every
survey row is what makes the gap traceable to the literature instead of asserted.

`scripts/build_script_doc.js` rewritten slide-for-slide to match: 1,330 spoken words
(~10 min) plus table-pointing time; new Q&A on literature selection and on how this differs
from INCOIS SVAS.

- *Correction:* re-reading Pillai & Nair (2010) against its abstract while building the
  survey table showed the synopsis had blended two Kerala studies. The 2010 paper covers
  2006–2010 and reports CPUE higher inside PFZ zones, ~2–6× catch and ~2–7× monetary
  benefit. The claim that benefit decays with delay after the satellite pass belongs to a
  different study and has been removed from `synopsis.md` and the Word build.
- *Not yet done:* visual QA of the rebuilt deck. PowerPoint is running on this machine in
  "Product Activation Failed" mode with the deck open, and in that state COM automation
  refuses to open files (HRESULT 0x80048240). The deck passes `validate.py`. It needs a
  rendered check before presenting — the survey and dataset tables are dense and PowerPoint
  grows rows to fit text.

### Step 26 · Two-page plain-language project brief

`scripts/build_brief_doc.js` → `docs/Sagar_Setu_Project_Brief.docx`, for a non-technical
reader: the idea, why it matters, how it works (and the one rule), what has been done, the
data, the tech stack, future objectives, and honest limitations. 984 words, A4, 10 pt.

- Page count is **estimated** at ~1.6 pages, not measured: Word is also running unactivated
  and refuses COM `Documents.Open` ("This command is not available"). Measure with
  `ComputeStatistics(2)` once Word is closed.

### Step 27 · Literature review rebuilt on eight recent, verified studies

The user supplied a ChatGPT literature review of 20 papers and asked for the synopsis and
deck to be remade around the 7–8 most relevant and recent of them.

**Selection (8 of 20), one or two per system component, half from 2023 or later:**
Kurup et al. 2024 (*Weather*, localised wind forecasts for small-boat fishers) · Sarangi et
al. 2024 (*Environ. Monit. Assess.*, multi-parameter PFZ) · Saka et al. 2021 (*MTSJ*, the
**Thoondil** app run by Tamil Nadu Fisheries) · Anabel et al. 2018 (*CSI Trans. ICT*, Fisher
Friend) · Vincent 2020 (*Maritime Affairs*, Palk Bay / IMBL) · Lewis et al. 2020 (RAG) ·
Niu et al. 2024 (*ACL*, RAGTruth) · Gala et al. 2023 (*TMLR*, IndicTrans2).
INCOIS SVAS and Jolliffe & Stephenson are kept as *methodology* references [9]–[10]; the
threshold calibration and the POD/FAR evaluation depend on them.

**Every one was verified against its DOI record via the Crossref API**, not taken from the
ChatGPT text. Corrections that surfaced:
- Sarangi et al. is vol. 196, issue 1, **article 98** (online Dec 2023), not "pp. 1–14".
- Anabel et al.'s co-authors are S. Velvizhi and D. Suvitha; vol. 6, issue 3–4, pp. 257–267.
- Saka et al. — search engines did not find it; the DOI resolved and Crossref returned the
  title, all 13 authors, pages 50–57, and an abstract describing **Thoondil**, which turns
  out to be the closest operational system to this project.
- Vincent 2020 — not found by search; found via a Crossref bibliographic query (16(2), 71–88).
- Two of ChatGPT's 20 were uncitable as given: "Nair et al. — PFZ advisories, are they
  beneficial" (no year/venue; actually Pillai & Nair 2010, and its fuel/search-time claim is
  not in the abstract) and "Validation of PFZ forecasts from Andaman and Nicobar" (no authors).

**Changes:**
- `synopsis.md` / `build_synopsis_doc.js`: §2 rewritten as seven subsections, each study
  ending in an explicit *limitation for this problem*; new comparison matrix (7 capability
  columns); §3 gaps G1–G6 re-evidenced against the new references, plus a gap → evidence →
  objective table; gap statement softened from "no published system" to **"we found no
  published system"** (the one piece of the ChatGPT advice worth adopting). 12 pages.
- Deck (`build_midterm_deck.js`): 10 slides — the three literature slides became two,
  four studies each; gap matrix, gap → objective table and references rebuilt.
- Script re-synced slide for slide; Q&A gains "How is this different from Thoondil or
  Fisher Friend?" and now argues from RAGTruth rather than the dropped survey.
- Brief: "15 verified papers" → "8 recent, verified studies".

**Rendered QA (PowerPoint and Word finally closed, so COM automation worked again):**
- Brief measured at exactly **2 pages** (`ComputeStatistics`), replacing Step 26's estimate.
- Slide 9: "93.9 %" wrapped, stranding the "%" on its own line. Fixed with a non-breaking
  space and narrower method card; the freed space now holds the 1/2/3-day lead table.
- Slides 3–4: tables left ~1.7 in of dead space; rows now sized to fill, text up to 14 pt.
- Script: 1,285 spoken words, 8.6–10.3 min at speaking pace.
- *Note:* files written through the Write tool store `\uXXXX` escapes as literal
  characters, so string replacements must match the literal glyphs — three Python
  `str.replace` calls silently missed for that reason and were redone with Edit.

### Step 28 · Explaining the non-monotonic hit rate

The day-ahead → 2-day → 3-day hit rates read 93.9 % → 97.0 % → 90.9 %, which looks abnormal
and will be questioned. Recomputed from the contingency counts rather than argued:

| Lead | Warned | Wilson 95 % CI | Warnings | False alarms | CSI |
|---|---|---|---|---|---|
| 1 d | 31 / 33 | 80.4–98.3 % | 32 | 1 | 91.2 % |
| 2 d | 32 / 33 | 84.7–99.5 % | 39 | 7 | 80.0 % |
| 3 d | 30 / 33 | 76.4–96.9 % | 43 | 13 | 65.2 % |

Only 33 of 460 harbour-mornings were do-not-sail, so one morning ≈ 3 points of POD; the
2-day "rise" is one morning, and the intervals overlap almost entirely. The 2-day forecast
bought that extra hit by warning more (39 vs 32 warnings, false alarms 1 → 7). CSI falls
monotonically, tracking wave-height MAE (0.06 → 0.10 → 0.12 m); because the worst parameter
decides, added forecast noise surfaces mostly as false alarms rather than misses.

The numbers were not changed. The presentation was: synopsis §5 and slide 9 now show the
counts (warned of 33, false alarms) and CIs next to the percentages, with a short "reading
the hit rate" note; the script gains a line on slide 9 and a prepared Q&A answer.

- Open-Meteo caps `past_days` at 92, so a larger sample needs the Previous Runs API with
  explicit date ranges — a full year spanning both monsoons would add Bay of Bengal rough
  seasons (Chennai and Port Blair had zero do-not-sail mornings in this window). Noted as
  planned in §5; not started.
- Removed the forced page break before §5 that left page 10 nearly empty.

### Step 29 · The fisherman question bank — and what it found

The supervisor asked for a bank of the questions fishermen actually ask. Built as a test set,
not training data: each entry records the **expected understanding** (type, place, day, time,
boat, language), never a fixed answer — "is it safe tomorrow" has a different right answer
every day, so a model trained on question/answer pairs would memorise stale answers.

- `data/question_bank/bank.json` — 49 questions across all 8 intents, in English, Tamil,
  Hindi and Malayalam, including colloquial, misspelled and code-mixed (romanised Hindi)
  phrasing, plus out-of-scope questions (cricket, phone recharge, fish market price).
- `scripts/run_question_bank.py` — runs each through the full graph, scores understanding
  field by field and the answer's behaviour (verdict where needed, every number verified,
  reply in the asker's language); retries if the model was rate-limited rather than scoring
  a quota error as a misunderstanding. Writes `results.json` and
  `docs/question_bank_results.md`, which doubles as a recorded run for the demo.
- Web: a **Question bank** panel (button in the header) lists all 49 by category with the
  last run's ✓ / ✗ per question; one click asks it. `GET /question-bank` serves it.
- `.claude/launch.json` gains the API server (the page needs both; only the web server was
  configured, which is why "it won't run" — the page loaded with nothing behind it);
  `.vscode/tasks.json` adds a one-click "Sagar Setu: start".

**Result: 49 / 49 understood, 49 / 49 answers behaved** — after the fixes below. The first
pass scored 20 / 24 on the questions it could score, and the misses were all real bugs:

| Question | Bug | Fix |
|---|---|---|
| "I **have** a 15 m boat at Veraval" → *Vashi(Haveli)* | substring match crossed a word boundary ("vash**i have**li"), and the first weak multi-word hit beat the exact "Veraval" later | whole-word substring matching; `_find_location` keeps the best-scoring span, exact match wins |
| "…Mangalore **this afternoon**" → tomorrow | no "this afternoon"; day words matched as substrings ("know" ⊃ "now") | added "this morning/afternoon/evening"; word-boundary matching |
| "which direction should I go … to **find fish**" → safety | "should i go" is a safety keyword, checked first | a find/where/direction…fish pattern is checked before the keyword table |
| "Kal subah Porbandar se boat … hai kya" → English | Latin-script Hindi read as English | ≥ 2 common Hindi words → language hi; kal/aaj/parso/subah/shaam/raat added |
| PFZ and chlorophyll answers with the model down | **the deterministic template failed its own verification**: it prints each observation's grid distance, its age ("0 min ago") and a signed z-score ("-0.62"), none in the allowed set | allowed numbers now include ledger distances and ages, and magnitudes of negative values |
| Tamil "why is the catch falling near Chennai" → general knowledge | planner prompt didn't exclude place-specific "why" questions | prompt: a named place asking what/why needs live data |
| "what does a **2 metre** swell mean" → unverified | the asker's own number counted as invented | for general-knowledge questions only, numbers from the question are allowed; forecasts stay strict (test pins both) |

**Gemini free tier.** The first full run exhausted `gemini-3.6-flash`'s daily quota
(`429 GenerateRequestsPerDayPerProjectPerModel-FreeTier`, retry ≈ 17.6 h), which also
explains every "model unavailable" in the second half. Free-tier quotas are **per model**, so:
- `GeminiLLM` now takes a fallback list (`GEMINI_FALLBACK_MODELS`, default
  `gemini-3.5-flash-lite,gemini-3.1-flash-lite`). A 429 or 503 parks that model for Google's
  `retryDelay` and the request moves on; network errors still fail fast.
- `gemini-3.5-flash-lite` answers `400 INVALID_ARGUMENT` to `thinkingConfig{thinkingBudget:0}`
  (probed: plain 200, json-mode 200, thinking-config 400). The client now learns that per
  model and resends without it.
- All 8 Indian-language questions passed on the lite model.

**Caught by reading the Tamil, not by any check:** the lite model rendered wind speed as
"15.3 நொடிகள்" (seconds) instead of knots. The verifier checks numbers, not units — the
limitation documented in the synopsis. Synthesis rule 8 now pins units and gives the word for
knots in Tamil, Hindi and Malayalam; re-asked live, it wrote "15.3 நாட்".

Tests: 115 → 124 (every bug above has a regression test). `results.json` merges the latest
run of each question; 10 early-run answers are deterministic templates written while the
model was out of quota, and are labelled as such in the report.

### Step 30 · Phase 5 — route optimisation

Bhashini is still blocked on keys, so Phase 5 moved to the next item in the build order:
"route optimisation first (demos best on a map)". A fisherman asks *"what is the best route
from Kochi to the fishing zone?"*; the system routes to the nearest INCOIS zone (or the one
named — "PFZ #2", "second zone"), draws it, and the risk engine grades the whole trip.

**Data first.** Open-Meteo answers a whole grid in one request: 81 points around Palk Bay in
1.6 s (marine) and 1.3 s (weather). Every point gets values — land points snap to the
nearest sea cell — so land and borders must come from our own polygons, not from nulls.
Checked the Palk Bay geometry before relying on it: the IMBL there sits very close to the
Indian coast (8 km east of Rameswaram; the bay's centre at 9.6°N 79.5°E is Sri Lankan
water), and the Indian side of the bay is classed `eez`, so it is navigable.

**`geo/route.py`** (pure, unit-tested): A* over ~2 km cells. Hard constraints: inside India's
EEZ, ≥ 2 km from every IMBL, off land (EEZ + land union, so land near the line is not
mistaken for foreign water). Cost = travel time at speed made good (current along the
heading) × a sea-state penalty that grows with wave height, wind and steepness relative to
the vessel's *caution* thresholds, and more on the bow than astern. Cells at the vessel's
do-not-sail level are avoided when any route avoids them; otherwise the route goes through and
the verdict says so. Path smoothing only takes shortcuts that stay in legal water — a test
samples every 0.5 km of the result. A destination in another state's water is refused.
The case that matters: between two Indian points whose straight line cuts into Sri Lankan
water at the IMBL's corner near 9.67°N 79.38°E, the route bends west, adds 3.2 km, and stays
3.7 km inside.

**Integration.** New intent `route` (route phrases outrank both the find-fish pattern and the
safety keywords; "PFZ #2" / "second zone" → `pfz_index`). The geospatial specialist — which
CLAUDE.md gives A* to — calls `plan_sea_route`, which fetches the grid through the normal
cache → live → stale-cache chain and writes the conditions at every node the route passes as
`route_*` observations. They are kept out of the harbour summary on purpose: the ledger's
`worst()` has no spatial filter, so sharing variable names would have paired the worst wave
with a period from a different node and corrupted the steepness check. Instead
`merge_route_conditions` raises the risk inputs to the route's worst, taking the period from
the same node. Live check: harbour 0.64 m, route 1.04 m — the verdict used 1.04 m.
No grid at all → the harbour forecast is applied to the whole area and the answer says so.
The brief gains route lines (legs as compass + km, time, margin, what the straight line
would have meant) and synthesis rule 9 requires the "not a navigation chart" sentence.
The map draws the route over a dashed straight line, red when that line would cross the IMBL.

**Question bank:** R01–R04 (English, Tamil, Hindi; one asks for zone #2). All pass:
**53 / 53 understood and behaved.**

**Limitations, stated plainly:**
- *Coastline.* Land comes from the Marine Regions EEZ outline, which is coarse at the scale of
  narrow islands and harbour channels. Rameswaram → Gulf of Mannar can slip across the
  Dhanushkodi strip; Kochi's route leaves southward rather than through the port channel.
  A higher-resolution land layer (e.g. Natural Earth 1:10m, public domain) would fix most of
  it — not yet added. Shallow water and sandbanks are not modelled at all.
- *Verifier blind spot, again.* The Tamil route answer wrote "five hours old" as a word
  (ஐந்து); the verifier only reads digits. True here, unchecked in general.
- Current direction is taken as the direction of flow (oceanographic convention) — not yet
  verified against Open-Meteo's documentation; it only affects travel time, not safety.

Tests 131 → 136.

### Step 31 · Saying where each threshold table came from

CLAUDE.md asks for three vessel tables but gives numbers for one. The traditional-craft
limits are the spec's starting values; the motorised and mechanised limits were set in Phase 2
by stepping each limit up for a larger hull (+0.5 m waves, +3–4 kt wind per class) — our
extrapolation, no source. Step 10 recorded that only as "progressively looser", which reads
as more authoritative than it is.

`TABLE_SOURCE` in `risk/thresholds.py` now names the origin of each table, every
`RiskVerdict.calibration` carries it (so the verdict card says "our extrapolation —
unsourced" for a 15 m boat), and `/health` reports it next to the numbers. A parametrised
test pins all three. The 92-day evaluation used only the traditional table, so its figures
are unaffected. Tests 136 → 139.

### Step 32 · Refreshing the offline snapshot — and a dishonest timestamp it exposed

The frozen snapshot (the offline fallback) dated from 2026-09-15. Refreshed for all five
harbours and the Gulf of Mannar: Open-Meteo marine and weather, NOAA chlorophyll and INCOIS
Argo all returned 200.

INCOIS's PFZ WFS did not: a 90 s ReadTimeout, twice. The PFZ file on disk stayed the
September advisory — but the manifest recorded the failed attempt's timestamp as its
`fetched_at`, so offline the system would have labelled a month-old advisory as fetched
today. That is exactly the hidden degradation CLAUDE.md rule 3 forbids.

`scripts/snapshot.py` now handles a failed source in `_keep_or_recover`:
1. if the app's runtime cache holds a newer copy of the same URL, promote it with its **true**
   fetch time and a note ("copied from the runtime cache: the live refresh failed");
2. otherwise keep the previous record untouched;
3. either way, record the failed attempt under `refresh_failed`.

Result: the snapshot's PFZ advisory is now 2026-10-15 (81 zones, Julian day 288), fetched
2026-10-16T04:49Z, with the 2026-10-18 failure recorded beside it.

- *Brittle test found:* `test_no_pfz_near_veraval_in_snapshot_returns_empty_not_a_guess`
  asserted that Gujarat had no advisory on the snapshot day — true in September, false after
  the refresh. Rewritten to build the "nothing in range" case from the data (drop the Gujarat
  zones) instead of assuming a particular day's advisory.

### Step 33 · A real coastline for routes — and the Andaman EEZ that was missing

Route search took "land" from the Marine Regions EEZ outline, which treats narrow islands as
sea: a route from Rameswaram to the Gulf of Mannar cut straight across Rameswaram island and
the Dhanushkodi spit.

- **Land mask:** Natural Earth 1:10m land + minor islands (public domain), clipped to the
  Indian region — `data/static/ne_10m_land_india_region.geojson`, 0.29 MB, loaded by the new
  `geo/land.py`. A grid cell is land if land touches **any part of its 2 km box**, not just
  its centre, so a spit narrower than a cell still blocks. Every smoothed leg is also checked
  against the exact coastline, and `check_line` now samples every 0.1 km.
- **Result:** Rameswaram → Gulf of Mannar PFZ now goes round the east of Dhanushkodi: 81.2 km,
  legs SE / SSW / W, never closer than 5.9 km to the IMBL. The answer says the straight line
  crosses land, which is why it is longer. The straight line is now measured from where the boat
  reaches open water, not from the harbour coordinate.
- **Stated, not invented:** at 1:10m the Pamban channel between Rameswaram island and the
  mainland is closed. We do not draw a passage the data does not show; the no-route reason
  names this limitation.

Testing all five harbours on the new mask found three more problems:

1. **Kochi:** the nearest water to the harbour is the Vembanad backwater, whose mouth is
   narrower than a cell, so the route snapped into a lagoon with no exit. The fix is
   `_snap_pair`: snap the open-sea end first, flood-fill the water connected to it, then
   snap the harbour into *that* water. Kochi now snaps 6.6 km to the open sea.
2. **Rameswaram:** the search window (0.15° pad) was too small to go round the spit. The
   minimum pad is now 0.3°; the forecast grid uses the same box.
3. **Port Blair — an older bug, found by this test:** `india_eez_polygon.geojson` held only
   the mainland EEZ (mrgid 8480). Marine Regions publishes the Andaman & Nicobar EEZ as a
   separate polygon (mrgid 8333). Without it, the sea off Port Blair was classified as
   "land or port", so the geofence never said "inside India's EEZ" there and every route
   failed. Fetched mrgid 8333 (free, no key, 0.36 MB) and appended it; `load_eez()` now
   unions all features.

`_snap` is now vectorised, so Kochi's search fell from about 900 ms to 110 ms.

Tests 140 → 148:
- a Rameswaram leg-by-leg land check;
- Kochi backwater snapping;
- each harbour reaching open sea (four parametrised cases);
- Andaman & Nicobar waters as Indian EEZ (three points).

Bank questions R01–R04 re-run: 4/4 understood and behaved. The bank total is still 53/53.
INCOIS PFZ timed out live during the run, and the answers said they used the stored copy.

*Commit note:* this whole step is in commit `c554538`, which is mislabelled "style: ruff
format". PowerShell 5.1 split the real message at its quote marks, so the first commit failed
and the formatting commit picked up everything that was staged. It was already pushed, so it
was left as it is rather than force-pushing `main`. Commits now take their message from a
file (`git commit -F`).

### Step 34 · Phase 6: the first "wifi off" rehearsal of the whole bank

`scripts/run_question_bank.py --offline` sends every request (data sources and Gemini) to a
dead proxy, and swaps the runtime cache for an empty temp folder, so every source falls to
the frozen snapshot. It writes `data/question_bank/results_offline.json` and
`docs/question_bank_offline.md`, and checks that every verdict answer states it was degraded.

**Result: 20 of 53 questions answered, and all 20 were correct and honest.** Each said
"snapshot" and used the template answer. The other 33 replied "language model unavailable".
Problems found, **not yet fixed**:

1. **Tamil and Hindi have no offline path.** `fast_plan` only handles Latin script, so every
   Tamil and Hindi question needs Gemini. Demo item #4 (a Tamil/Hindi round trip) fails with
   the network down.
   - Fix: Tamil and Hindi keywords and day words in the fast path.
   - Fix: Tamil and Devanagari aliases for the landing centres.
   - Fix: Tamil and Hindi templates for the offline answer, which a native speaker should
     review.
2. **The "model unavailable" message is in English** even for a Tamil question (Q02).
3. **It is slow offline.** On a network that times out rather than refuses, each source waits
   its full timeout (Open-Meteo 2 s, PFZ about 4 s), and Gemini is retried on every question
   (3.7 s). A safety answer took 8.4 s against the 2.4 s budget.
   - Fix: a per-host circuit breaker in `sources/base.py` and `agents/llm.py`. After a
     connection failure, skip that host for about 60 s and go straight to the fallback.
4. General-knowledge and off-topic questions also need the model. Offline, "model
   unavailable" is an acceptable honest answer for them.
