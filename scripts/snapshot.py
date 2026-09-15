"""Phase 1: fetch every verified source for every test harbour and freeze it.

Writes data/snapshots/<harbour>/<source>.json with the raw response, and
data/snapshots/manifest.json recording URL, status, latency and fetched_at for
each call. This is the offline fallback — the system must answer from it alone.

Run:  uv run python scripts/snapshot.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
import truststore

# INCOIS serves an incomplete TLS chain; the OS trust store resolves it where certifi does not.
truststore.inject_into_ssl()

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from marine.config import SNAPSHOT_DIR  # noqa: E402
from marine.fixtures import GULF_OF_MANNAR, HARBOURS  # noqa: E402

POINTS = {**HARBOURS, "gulf_of_mannar": GULF_OF_MANNAR}

MARINE_VARS = ",".join(
    [
        "wave_height",
        "wave_period",
        "wave_direction",
        "swell_wave_height",
        "swell_wave_period",
        "swell_wave_direction",
        "wind_wave_height",
        "wind_wave_period",
        "sea_surface_temperature",
        "ocean_current_velocity",
        "ocean_current_direction",
    ]
)
WEATHER_VARS = ",".join(
    [
        "wind_speed_10m",
        "wind_gusts_10m",
        "wind_direction_10m",
        "visibility",
        "precipitation",
        "weather_code",
        "cape",
    ]
)


def griddap(url: str) -> str:
    """Tomcat behind INCOIS rejects literal brackets; ERDDAP griddap needs them percent-encoded."""
    return url.replace("[", "%5B").replace("]", "%5D")


def point_sources(lat: float, lon: float) -> dict[str, str]:
    """Per-harbour request URLs. These are the exact shapes the sources/ modules will use."""
    chl_start = "2026-08-15T12:00:00Z"
    return {
        "open_meteo_marine": (
            "https://marine-api.open-meteo.com/v1/marine"
            f"?latitude={lat}&longitude={lon}&hourly={MARINE_VARS}"
            "&past_days=7&forecast_days=8&timezone=UTC"
        ),
        "open_meteo_weather": (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}&hourly={WEATHER_VARS}"
            "&wind_speed_unit=kn&past_days=7&forecast_days=8&timezone=UTC"
        ),
        # NOAA VIIRS gap-filled NRT chlorophyll — open fallback for Copernicus BGC.
        "noaa_viirs_chl": griddap(
            "https://coastwatch.noaa.gov/erddap/griddap/noaacwNPPN20VIIRSDINEOFDaily.json"
            f"?chlor_a[({chl_start}):(last)][(0.0)][({lat})][({lon})]"
        ),
        # INCOIS Argo 10-day gridded temperature, surface level, latest field.
        "incois_argo_temp": griddap(
            "https://erddap.incois.gov.in/erddap/griddap/incois_argo_10d_VAM.json"
            f"?TEMP[(last)][(5)][({lat})][({lon})]"  # 1° grid, 5 m top level
        ),
    }


GLOBAL_SOURCES = {
    "incois_pfz_lines": (
        "https://incois.gov.in/geoserver/PFZ_Automation/ows?service=WFS&version=1.1.0"
        "&request=GetFeature&typeName=PFZ_Automation:pfzlines&outputFormat=application/json"
    ),
}


async def fetch(client: httpx.AsyncClient, name: str, url: str, out: Path) -> dict:
    t0 = time.perf_counter()
    rec: dict = {"source": name, "url": url, "fetched_at": datetime.now(UTC).isoformat()}
    try:
        r = await client.get(url)
        rec["status"] = r.status_code
        rec["latency_ms"] = round((time.perf_counter() - t0) * 1000)
        rec["bytes"] = len(r.content)
        if r.status_code == 200:
            try:
                payload = r.json()
            except ValueError:
                payload = {"_raw_text": r.text[:4000]}
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(payload), encoding="utf-8")
            rec["file"] = str(out.relative_to(SNAPSHOT_DIR.parent.parent))
        else:
            rec["error"] = r.text[:300]
    except Exception as e:  # noqa: BLE001 — we want every failure recorded, not raised
        rec["status"] = None
        rec["latency_ms"] = round((time.perf_counter() - t0) * 1000)
        rec["error"] = f"{type(e).__name__}: {e}"
    flag = "ok " if rec.get("status") == 200 else "ERR"
    print(f"  [{flag}] {name:<22} {rec['latency_ms']:>6} ms  {rec.get('error', '')}")
    return rec


async def main() -> None:
    manifest: dict = {"created_at": datetime.now(UTC).isoformat(), "points": {}, "global": {}}
    # NOAA CoastWatch returns 403 to the default python-httpx User-Agent.
    headers = {"User-Agent": "Mozilla/5.0 SagarSetu/0.1 (marine decision support; research)"}
    async with httpx.AsyncClient(timeout=90, follow_redirects=True, headers=headers) as client:
        print("global sources")
        for name, url in GLOBAL_SOURCES.items():
            manifest["global"][name] = await fetch(client, name, url, SNAPSHOT_DIR / f"{name}.json")
        for harbour, (lat, lon) in POINTS.items():
            print(f"{harbour} ({lat}, {lon})")
            manifest["points"][harbour] = {"lat": lat, "lon": lon, "sources": {}}
            tasks = [
                fetch(client, name, url, SNAPSHOT_DIR / harbour / f"{name}.json")
                for name, url in point_sources(lat, lon).items()
            ]
            for rec in await asyncio.gather(*tasks):
                manifest["points"][harbour]["sources"][rec["source"]] = rec
    (SNAPSHOT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"\nwrote {SNAPSHOT_DIR / 'manifest.json'}")


if __name__ == "__main__":
    asyncio.run(main())
