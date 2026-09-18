"""Export human-readable samples of every dataset the system uses to docs/datasets/.

Everything written here comes from data we actually fetched (the committed snapshot and
static files, plus a live Copernicus subset). Nothing is synthesised. Run:

  uv run python scripts/export_datasets.py            # snapshot + static only (offline)
  uv run python scripts/export_datasets.py --copernicus   # also pull a Copernicus sample
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from marine.config import ROOT, SNAPSHOT_DIR, STATIC_DIR  # noqa: E402
from marine.fixtures import HARBOURS  # noqa: E402

OUT = ROOT / "docs" / "datasets"
POINTS = {**HARBOURS, "gulf_of_mannar": (9.15, 79.40)}


def write(name: str, header: list[str], rows: list[list]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / name
    with p.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  {name:<40} {len(rows):>6} rows")


def load(harbour: str, key: str) -> dict | None:
    p = SNAPSHOT_DIR / harbour / f"{key}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def export_open_meteo(key: str, name: str) -> None:
    rows, header = [], None
    for h in POINTS:
        d = load(h, key)
        if not d:
            continue
        hourly = d["hourly"]
        vars_ = [k for k in hourly if k != "time"]
        if header is None:
            header = ["harbour", "grid_lat", "grid_lon", "time_utc", *vars_]
        for i, t in enumerate(hourly["time"]):
            rows.append([h, d["latitude"], d["longitude"], t, *[hourly[v][i] for v in vars_]])
    write(name, header, rows)


def export_units(key: str, name: str) -> None:
    d = load("kochi", key)
    write(name, ["variable", "unit"], [[k, v] for k, v in d["hourly_units"].items()])


def export_pfz() -> None:
    d = json.loads((SNAPSHOT_DIR / "incois_pfz_lines.json").read_text(encoding="utf-8"))
    rows = []
    for f in d["features"]:
        p, g = f["properties"], f["geometry"]
        pts = [pt for line in g["coordinates"] for pt in line]
        adv = date(int(p["Year"]), 1, 1) + timedelta(days=int(p["Julian_day"]) - 1)
        rows.append(
            [
                p["UID"],
                p["State_Name"],
                adv.isoformat(),
                p["Year"],
                p["Julian_day"],
                round(float(p["Length"]), 2),
                len(pts),
                round(pts[0][1], 4),
                round(pts[0][0], 4),
                round(pts[-1][1], 4),
                round(pts[-1][0], 4),
            ]
        )
    write(
        "incois_pfz_lines.csv",
        [
            "uid",
            "state",
            "advisory_date",
            "year",
            "julian_day",
            "length_km",
            "n_vertices",
            "start_lat",
            "start_lon",
            "end_lat",
            "end_lon",
        ],
        rows,
    )
    # every vertex, for plotting
    vrows = [
        [f["properties"]["UID"], f["properties"]["State_Name"], i, round(pt[1], 5), round(pt[0], 5)]
        for f in d["features"]
        for i, pt in enumerate(pt for line in f["geometry"]["coordinates"] for pt in line)
    ]
    write("incois_pfz_vertices.csv", ["uid", "state", "vertex", "lat", "lon"], vrows)


def export_landing_centres() -> None:
    d = json.loads((STATIC_DIR / "incois_landing_centres.geojson").read_text(encoding="utf-8"))
    rows = [
        [
            p["LC_NAME"],
            p["DIST_NAME"],
            p["SECTOR_NAM"],
            p["SECTOR_ID"],
            p["LATITUDE"],
            p["LONGITUDE"],
        ]
        for p in (f["properties"] for f in d["features"])
    ]
    write(
        "incois_landing_centres.csv",
        ["landing_centre", "district", "sector", "sector_id", "lat", "lon"],
        rows,
    )


def export_sectors() -> None:
    d = json.loads((STATIC_DIR / "incois_pfz_sectors.geojson").read_text(encoding="utf-8"))
    rows = []
    for f in d["features"]:
        p = f["properties"]
        ring = f["geometry"]["coordinates"][0][0]
        lons, lats = [c[0] for c in ring], [c[1] for c in ring]
        rows.append(
            [
                p["SECTORNAME"],
                p["SEC_ID"],
                round(min(lats), 3),
                round(max(lats), 3),
                round(min(lons), 3),
                round(max(lons), 3),
            ]
        )
    write(
        "incois_pfz_sectors.csv",
        ["sector", "sector_id", "lat_min", "lat_max", "lon_min", "lon_max"],
        rows,
    )


def export_boundaries() -> None:
    d = json.loads((STATIC_DIR / "india_eez_boundaries.geojson").read_text(encoding="utf-8"))
    rows = []
    for f in d["features"]:
        p, g = f["properties"], f["geometry"]
        n = (
            sum(len(line) for line in g["coordinates"])
            if g["type"] == "MultiLineString"
            else len(g["coordinates"])
        )
        rows.append(
            [
                p.get("line_name"),
                p.get("line_type"),
                p.get("sovereign1"),
                p.get("sovereign2"),
                p.get("mrgid"),
                n,
                "yes" if p.get("line_type") in ("Treaty", "Median line", "Court ruling") else "no",
            ]
        )
    write(
        "marine_regions_boundaries.csv",
        [
            "line_name",
            "line_type",
            "sovereign1",
            "sovereign2",
            "mrgid",
            "n_vertices",
            "used_as_imbl",
        ],
        rows,
    )
    e = json.loads((STATIC_DIR / "india_eez_polygon.geojson").read_text(encoding="utf-8"))[
        "features"
    ][0]["properties"]
    write(
        "marine_regions_eez_polygon.csv",
        ["field", "value"],
        [
            [k, e[k]]
            for k in ("geoname", "mrgid", "sovereign1", "territory1", "area_km2", "pol_type")
        ],
    )


def export_chl() -> None:
    rows = []
    for h in POINTS:
        d = load(h, "noaa_viirs_chl")
        if not d:
            continue
        cols = d["table"]["columnNames"]
        for r in d["table"]["rows"]:
            rec = dict(zip(cols, r, strict=False))
            rows.append([h, rec["time"][:10], rec["latitude"], rec["longitude"], rec["chlor_a"]])
    write(
        "noaa_viirs_chlorophyll.csv",
        ["harbour", "date", "grid_lat", "grid_lon", "chlor_a_mg_m3"],
        rows,
    )


def export_argo() -> None:
    rows = []
    for h in POINTS:
        d = load(h, "incois_argo_temp")
        if not d:
            continue
        cols = d["table"]["columnNames"]
        for r in d["table"]["rows"]:
            rec = dict(zip(cols, r, strict=False))
            rows.append(
                [h, rec["time"][:10], rec["ZAX"], rec["latitude"], rec["longitude"], rec["TEMP"]]
            )
    write(
        "incois_argo_temperature.csv",
        ["harbour", "date", "depth_m", "grid_lat", "grid_lon", "temp_degC"],
        rows,
    )


def export_manifest() -> None:
    m = json.loads((SNAPSHOT_DIR / "manifest.json").read_text(encoding="utf-8"))
    rows = [
        [
            "global",
            "",
            "",
            k,
            v["url"],
            v.get("status"),
            v.get("latency_ms"),
            v.get("bytes"),
            v["fetched_at"],
        ]
        for k, v in m["global"].items()
    ]
    for h, p in m["points"].items():
        for k, v in p["sources"].items():
            rows.append(
                [
                    h,
                    p["lat"],
                    p["lon"],
                    k,
                    v["url"],
                    v.get("status"),
                    v.get("latency_ms"),
                    v.get("bytes"),
                    v["fetched_at"],
                ]
            )
    write(
        "fetch_manifest.csv",
        [
            "point",
            "lat",
            "lon",
            "source",
            "url",
            "http_status",
            "latency_ms",
            "bytes",
            "fetched_at_utc",
        ],
        rows,
    )


def export_copernicus() -> None:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
    import copernicusmarine as cm

    u, pw = os.environ.get("COPERNICUS_USERNAME"), os.environ.get("COPERNICUS_PASSWORD")
    if not (u and pw):
        print("  copernicus: no credentials in .env, skipped")
        return
    rows = []
    for h, (lat, lon) in POINTS.items():
        ds = cm.open_dataset(
            dataset_id="cmems_mod_glo_bgc-pft_anfc_0.25deg_P1D-m",
            variables=["chl"],
            minimum_longitude=lon - 0.3,
            maximum_longitude=lon + 0.3,
            minimum_latitude=lat - 0.3,
            maximum_latitude=lat + 0.3,
            minimum_depth=0,
            maximum_depth=1,
            start_datetime="2026-07-01",
            username=u,
            password=pw,
        )
        sub = ds.chl.isel(depth=0).mean(dim=["latitude", "longitude"])
        for t, v in zip(sub.time.values, sub.values, strict=False):
            if v == v:  # not NaN
                rows.append([h, str(t)[:10], round(float(v), 4)])
        print(f"  copernicus {h}: {sub.time.size} days")
    write(
        "copernicus_chlorophyll_forecast.csv", ["harbour", "date", "chl_mg_m3_0.25deg_mean"], rows
    )
    # five-year daily baseline at one harbour, to show the depth of the record
    lat, lon = HARBOURS["kochi"]
    ds = cm.open_dataset(
        dataset_id="cmems_mod_glo_bgc-pft_anfc_0.25deg_P1D-m",
        variables=["chl"],
        minimum_longitude=lon - 0.3,
        maximum_longitude=lon + 0.3,
        minimum_latitude=lat - 0.3,
        maximum_latitude=lat + 0.3,
        minimum_depth=0,
        maximum_depth=1,
        username=u,
        password=pw,
    )
    sub = ds.chl.isel(depth=0).mean(dim=["latitude", "longitude"])
    write(
        "copernicus_chlorophyll_kochi_2021_2026.csv",
        ["date", "chl_mg_m3"],
        [
            [str(t)[:10], round(float(v), 4)]
            for t, v in zip(sub.time.values, sub.values, strict=False)
            if v == v
        ],
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--copernicus", action="store_true")
    a = ap.parse_args()
    print(f"writing to {OUT}")
    export_open_meteo("open_meteo_marine", "open_meteo_marine_hourly.csv")
    export_units("open_meteo_marine", "open_meteo_marine_units.csv")
    export_open_meteo("open_meteo_weather", "open_meteo_weather_hourly.csv")
    export_units("open_meteo_weather", "open_meteo_weather_units.csv")
    export_pfz()
    export_landing_centres()
    export_sectors()
    export_boundaries()
    export_chl()
    export_argo()
    export_manifest()
    if a.copernicus:
        export_copernicus()


if __name__ == "__main__":
    main()
