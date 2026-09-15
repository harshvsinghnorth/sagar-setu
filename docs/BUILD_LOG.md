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
