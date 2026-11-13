# Data sources — verified live on 2026-09-15

Every endpoint below was hit from this machine before any code was written against it.
Status is what actually happened, not what the documentation says.

## Summary

| Source | Verdict | Role in the chain |
|---|---|---|
| Open-Meteo marine + forecast | ✅ live, no key, 250–1300 ms | **Primary** for waves, swell, wind, visibility, SST, currents. Reliability floor. |
| INCOIS PFZ (GeoServer WFS) | ✅ live GeoJSON, no key, 1–8 s (1.1 MB). ⚠ 2026-11-13: HTTP 200 but only 2 zones dated 2026-09-04 | **Only** PFZ source. Fetch once per day, cache. Advisories older than 3 days are flagged in the answer. |
| INCOIS landing centres + sectors (WFS) | ✅ static | Location resolver (1223 named landing centres) + sector polygons. Committed. |
| Marine Regions EEZ polygon + boundaries | ✅ static, 38 s for 1.85 MB | Committed to `data/static/`. Never fetched at runtime. Mainland (mrgid 8480) **and** Andaman & Nicobar (mrgid 8333, added 2026-10-19) — separate polygons upstream. |
| Natural Earth 1:10m land + minor islands | ✅ static, public domain, clipped to 0.29 MB | Land mask for route search (`data/static/ne_10m_land_india_region.geojson`). Added 2026-10-19. |
| NOAA VIIRS chlorophyll (CoastWatch ERDDAP) | ✅ live, 1–2 s, needs browser UA | Chlorophyll. Copernicus substitute. |
| INCOIS ERDDAP Argo 10-day T/S | ⚠️ live but 1° grid, ~6 weeks stale, null nearshore | Weak SST cross-check. Ledger shows the staleness. |
| INCOIS ERDDAP everything else | ❌ stale (SST→2011, chl→2006, ASCAT→2023) | Climatology baseline only, if at all. |
| IMD `api.imd.gov.in/api/v1/*` | ❌ 401 `API key missing` | **No cyclone track / lightning / district warnings until we get a key.** |
| IMD `mausam.imd.gov.in/api/*` | ❌ IP whitelist | Same. |
| Copernicus Marine | ❌ needs free account | Register at marine.copernicus.eu to unlock BGC + physics. Optional. |
| Bhashini | untested (phase 5) | Needs keys. IndicTrans2 fallback planned. |

**Consequence for the risk engine:** lightning and cyclone-cone parameters have no live feed
today. The engine still implements them (with unit tests) and the ledger reports
`"no source available"` for those variables — the verdict is computed on what we have and
the answer says what is missing. Open-Meteo `cape` and `weather_code` (thunderstorm codes
95–99) give a *proxy* for convective risk and are recorded as such, never as lightning.

---

## Open-Meteo marine

```
GET https://marine-api.open-meteo.com/v1/marine
    ?latitude=9.97&longitude=76.28
    &hourly=wave_height,wave_period,wave_direction,swell_wave_height,swell_wave_period,
            swell_wave_direction,wind_wave_height,wind_wave_period,sea_surface_temperature,
            ocean_current_velocity,ocean_current_direction
    &past_days=7&forecast_days=8&timezone=UTC
```

Response: `{latitude, longitude, generationtime_ms, hourly_units:{…}, hourly:{time:[…], wave_height:[…], …}}`.
Units: wave_height m, period s, direction °, SST °C, **current velocity km/h** (convert to kt).
`latitude/longitude` in the response is the **grid node**, not the query point — Kochi
snaps to (9.958, 76.208), ~8 km. Store that as `distance_km`. Arrays contain `null` for
land/missing.

## Open-Meteo weather

```
GET https://api.open-meteo.com/v1/forecast
    ?latitude=…&longitude=…
    &hourly=wind_speed_10m,wind_gusts_10m,wind_direction_10m,visibility,precipitation,weather_code,cape
    &wind_speed_unit=kn&past_days=7&forecast_days=8&timezone=UTC
```

Units: wind kn (requested), visibility **m**, precipitation mm, cape J/kg. Weather codes
95/96/99 = thunderstorm. Grid node ≈ 1–2 km from the query point on land-adjacent cells.

## INCOIS PFZ — GeoServer WFS (undocumented; what `incois.gov.in/geoportal/MFASPFZ` calls)

```
GET https://incois.gov.in/geoserver/PFZ_Automation/ows?service=WFS&version=1.1.0
    &request=GetFeature&typeName=PFZ_Automation:pfzlines&outputFormat=application/json
```

FeatureCollection of `MultiLineString`, 87 features on 2026-09-15. Properties:
`State_Name` (KERALA, GOA, …), `Julian_day` ("257"), `Year` (2026), `Sno`, `UID`
(`YYYYDDDNNN`), `Length` (km), `SECTORBOUN`. Advisory date = Year + Julian_day.
There is **no depth or catch info** per line — the PFZ *text* advisory is not exposed
here. Sectors with no line on a given day (TN, GJ, MH on 2026-09-15) simply have no
features; the system must say "no advisory for your sector today".

Bearing and distance from a harbour are **computed by us** (nearest point on the line,
great-circle). The landing-centre layer has BEARING/DISTANCE fields but they are frozen at
2024-04-27 — do not use them.

Other layers (all static, committed under `data/static/`):
- `PFZ_Sectors:sector_new` — 14 sector polygons, `SECTORNAME`, `SEC_ID`.
- `PFZ_LandingCentres:LandingCenters_29Apr2024` — 1223 points, `LC_NAME`, `DIST_NAME`, `SECTOR_ID`.
- `PFZ_EEZ:indiaeez` — EEZ as lines (map overlay only; polygon comes from Marine Regions).

## Marine Regions (VLIZ)

```
GET https://geo.vliz.be/geoserver/MarineRegions/wfs?service=WFS&version=1.0.0&request=GetFeature
    &typeName=MarineRegions:eez&cql_filter=mrgid=8480&outputFormat=application/json        # India EEZ polygon
    &typeName=MarineRegions:eez_boundaries&cql_filter=sovereign1='India' OR sovereign2='India'  # IMBL lines
```

The Andaman & Nicobar EEZ is a separate feature: the same request with `cql_filter=mrgid=8333`
(200, 0.36 MB, 4.5 s on 2026-10-19). `india_eez_polygon.geojson` holds both; `load_eez()`
unions them.

## Natural Earth 1:10m land (route land mask)

`ne_10m_land` + `ne_10m_minor_islands` from naturalearthdata.com — public domain, no key.
Clipped to lon 64–100, lat 0–27 and rounded to 1e-5° → 0.29 MB, 13,662 vertices. Finer than
the EEZ outline (Rameswaram island and the Dhanushkodi spit are land), still a 1:10 000 000
product: it closes the Pamban channel and misses small harbour features such as Kochi's
inlet. Routes are advice, never a chart.

`eez_boundaries` feature `eez_boundaries.117` is the India–Sri Lanka line through Palk Bay /
Gulf of Mannar starting at (79.533, 9.10). Properties include `line_name`, `sovereign1/2`,
`line_type`.

## Cyclone and lightning without the IMD key (tested 2026-11-04, built 2026-11-13: `sources/gdacs.py`, `sources/sachet.py`)

### GDACS: tropical cyclones (no key)

```
GET https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH?eventlist=TC&alertlevel=green;orange;red
    (optional fromDate, toDate)                                                     # ~1.2 s, GeoJSON
GET https://www.gdacs.org/gdacsapi/api/events/geteventdata?eventtype=TC&eventid=…   # lists episodes
GET https://www.gdacs.org/gdacsapi/api/polygons/getgeometry?eventtype=TC&eventid=…&episodeid=…
```

- Geometry took 5.5 s, over the 2 s budget: fetch it in the background and cache it, only when
  a storm is active in the basin.
- `Class` values: `Poly_Cones` (forecast cone), `Poly_Green` / `Poly_Orange` / `Poly_Red` (wind
  fields; the Green label read "60 km/h"; `featuretype` absent = whole swath, `WindRadii` = one
  time), `Line_Line_n` (track, with `forecast` true/false), `Point_Polygon_Point_n` (positions).
- `polygondate` on lines and points is the **advisory's** date. A position's own time is in
  `polygonlabel`, e.g. "03/11 12:00 UTC".
- Each north Indian Ocean storm listed gives `source: JTWC`, so this is not IMD data.
- Advisory 9 of Arnab (eventid 1001345) returned "No data found": handle missing geometry.
- Intensity text can be inconsistent: Arnab reads "Tropical Storm (maximum wind speed of 222 km/h)".
- Terms of use not yet checked.

### SACHET (NDMA): official warnings, including lightning (no key)

```
GET https://sachet.ndma.gov.in/cap_public_website/FetchAllAlertDetails   # active alerts, JSON, ~0.85 s
GET https://sachet.ndma.gov.in/cap_public_website/rss/rss_india.xml      # latest 100 items
GET https://sachet.ndma.gov.in/cap_public_website/FetchXMLFile?identifier=…   # one CAP 1.2 message
```

- JSON fields include `disaster_type`, `severity`, `severity_level`, `effective_start_time`,
  `effective_end_time`, `area_description`, `centroid` ("lon,lat"), `area_covered` (apparently km²),
  `alert_source`, `warning_message` (often in a regional language).
- Senders seen: IMD regional offices and state disaster authorities.
- CAP messages have an `en-IN` info block but no polygon in the 12 checked.
- 40 sampled alerts were valid for 1–3.1 h, so they apply to the next few hours only.
- CAP `scope` is Public, but no licence or terms of reuse were found: ask NDMA before any public
  launch.

### Also checked

| Source | Result |
|---|---|
| JTWC RSS `metoc.navy.mil/jtwc/rss/jtwc.rss` | ✅ open; links warning text and data per storm. Possible backup. Not parsed yet. |
| IMD RSMC New Delhi `rsmcnewdelhi.imd.gov.in` | ✅ pages open without a key; products look like PDFs. Official, but not parsed yet. |
| Open-Meteo `lightning_potential` | ❌ all 48 hours empty at Kochi. |
| Blitzortung | ❌ forum posts say raw data is restricted and not for storm warnings. |

## NOAA CoastWatch VIIRS chlorophyll (gap-filled, near-real-time)

```
GET https://coastwatch.noaa.gov/erddap/griddap/noaacwNPPN20VIIRSDINEOFDaily.json
    ?chlor_a[(2026-08-15T12:00:00Z):(last)][(0.0)][(9.97)][(76.28)]
```

Requires a non-default `User-Agent` (403 otherwise). Brackets must be percent-encoded.
Response: `{table:{columnNames:[time,altitude,latitude,longitude,chlor_a], rows:[[…]]}}`,
mg m⁻³, ~4 km grid, latency to today ≈ 3 days. `pfeg.noaa.gov` host redirects here.

## INCOIS ERDDAP Argo

```
GET https://erddap.incois.gov.in/erddap/griddap/incois_argo_10d_VAM.json
    ?TEMP[(last)][(5)][(13.09)][(80.29)]
```

Requires `truststore` (OS trust store) — the server's chain fails against certifi.
1° grid, ZAX levels start at 5 m, latest field 2026-07-30, `null` on coastal cells.

## IMD

`https://api.imd.gov.in/api/v1/{cyclone_track,cyclone_cou,nowcast,district_warning,lightning}`
→ `401 {"error":"API key missing"}`. `mausam.imd.gov.in/api/nowcast_district_api.php` →
`Your IP … needs to be whitelisted`. **Action for the team: request an IMD API key.**
The source module exists and activates when `IMD_API_KEY` is set.

## Snapshot

`uv run python scripts/snapshot.py` refreshes `data/snapshots/` (5 harbours + Gulf of
Mannar, 7 days past + 8 days forecast, chlorophyll since 15 Aug, PFZ lines, Argo) and
writes `manifest.json` with URL / status / latency / `fetched_at` per call.
