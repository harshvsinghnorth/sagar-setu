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
from marine.sources.base import cache_read  # noqa: E402

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


def _keep_or_recover(new: dict, old: dict | None, url: str, out: Path) -> dict:
    """A failed refresh must not stamp today's date on yesterday's file.

    1. If the app's own runtime cache holds a copy of this URL that is newer than the old
       snapshot, promote it — real data, with its TRUE fetch time.
    2. Otherwise keep the previous record unchanged (its file is untouched on disk).
    Either way the failed attempt is recorded, so the manifest never hides it.
    """
    if new.get("status") == 200:
        return new
    failed = {"at": new["fetched_at"], "error": new.get("error")}
    cached = cache_read(url)
    old_at = datetime.fromisoformat(old["fetched_at"]) if old and old.get("status") == 200 else None
    if cached and (old_at is None or cached[1] > old_at):
        payload, fetched_at = cached
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload), encoding="utf-8")
        print(f"         recovered from the runtime cache, fetched {fetched_at.isoformat()}")
        return {
            "source": new["source"], "url": url, "fetched_at": fetched_at.isoformat(),
            "status": 200, "file": str(out.relative_to(SNAPSHOT_DIR.parent.parent)),
            "note": "copied from the runtime cache: the live refresh failed",
            "refresh_failed": failed,
        }
    if old and old.get("status") == 200:
        print(f"         kept the previous snapshot from {old['fetched_at']}")
        return {**old, "refresh_failed": failed}
    return new


async def main() -> None:
    prev_path = SNAPSHOT_DIR / "manifest.json"
    prev = json.loads(prev_path.read_text(encoding="utf-8")) if prev_path.exists() else {}
    manifest: dict = {"created_at": datetime.now(UTC).isoformat(), "points": {}, "global": {}}
    # NOAA CoastWatch returns 403 to the default python-httpx User-Agent.
    headers = {"User-Agent": "Mozilla/5.0 SagarSetu/0.1 (marine decision support; research)"}
    async with httpx.AsyncClient(timeout=90, follow_redirects=True, headers=headers) as client:
        print("global sources")
        for name, url in GLOBAL_SOURCES.items():
            out = SNAPSHOT_DIR / f"{name}.json"
            rec = await fetch(client, name, url, out)
            manifest["global"][name] = _keep_or_recover(
                rec, prev.get("global", {}).get(name), url, out
            )
        for harbour, (lat, lon) in POINTS.items():
            print(f"{harbour} ({lat}, {lon})")
            manifest["points"][harbour] = {"lat": lat, "lon": lon, "sources": {}}
            urls = point_sources(lat, lon)
            tasks = [
                fetch(client, name, url, SNAPSHOT_DIR / harbour / f"{name}.json")
                for name, url in urls.items()
            ]
            old_src = prev.get("points", {}).get(harbour, {}).get("sources", {})
            for rec in await asyncio.gather(*tasks):
                name = rec["source"]
                manifest["points"][harbour]["sources"][name] = _keep_or_recover(
                    rec, old_src.get(name), urls[name], SNAPSHOT_DIR / harbour / f"{name}.json"
                )
    (SNAPSHOT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"\nwrote {SNAPSHOT_DIR / 'manifest.json'}")


if __name__ == "__main__":
    asyncio.run(main())
