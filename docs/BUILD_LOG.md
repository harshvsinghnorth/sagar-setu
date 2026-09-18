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
