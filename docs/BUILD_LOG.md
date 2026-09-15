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
