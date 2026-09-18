"""Two figures for the dataset review, drawn from the exported CSVs — nothing synthetic.

  docs/datasets/map_datasets.png       PFZ lines, maritime boundaries, EEZ edge, harbours
  docs/datasets/chlorophyll_kochi.png  five years of daily chlorophyll at Kochi, two sources

Colours: three categorical slots from the validated reference palette (blue, orange, aqua)
plus neutral ink — identity is also carried by line style and direct labels, never by colour
alone.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from marine.config import ROOT, STATIC_DIR  # noqa: E402
from marine.fixtures import HARBOURS  # noqa: E402

D = ROOT / "docs" / "datasets"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, GRID, LAND = "#0b0b0b", "#52514e", "#e4e3df", "#f1f0ec"
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.edgecolor": GRID,
        "axes.labelcolor": INK2,
        "xtick.color": INK2,
        "ytick.color": INK2,
    }
)


def read(name: str) -> list[dict]:
    with (D / name).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def plot_map() -> None:
    fig, ax = plt.subplots(figsize=(10, 9), dpi=150)
    ax.set_facecolor("#fcfcfb")
    # land (EEZ+land union minus EEZ) — draw the union in light fill, then the EEZ edge
    union = json.loads((STATIC_DIR / "india_eez_land_union.geojson").read_text(encoding="utf-8"))
    for f in union["features"]:
        for poly in f["geometry"]["coordinates"]:
            ring = poly[0]
            ax.fill([c[0] for c in ring], [c[1] for c in ring], color=LAND, lw=0, zorder=1)
    eez = json.loads((STATIC_DIR / "india_eez_polygon.geojson").read_text(encoding="utf-8"))
    for poly in eez["features"][0]["geometry"]["coordinates"]:
        ring = poly[0]
        ax.plot([c[0] for c in ring], [c[1] for c in ring], color=INK2, lw=0.8, zorder=2)
    # maritime boundaries with another state
    b = json.loads((STATIC_DIR / "india_eez_boundaries.geojson").read_text(encoding="utf-8"))
    for f in b["features"]:
        if f["properties"].get("line_type") not in ("Treaty", "Median line", "Court ruling"):
            continue
        g = f["geometry"]
        parts = g["coordinates"] if g["type"] == "MultiLineString" else [g["coordinates"]]
        for part in parts:
            ax.plot(
                [c[0] for c in part], [c[1] for c in part], color=ORANGE, lw=1.6, ls="--", zorder=3
            )
    # PFZ lines
    verts = defaultdict(list)
    for r in read("incois_pfz_vertices.csv"):
        verts[r["uid"]].append((float(r["lon"]), float(r["lat"])))
    for pts in verts.values():
        ax.plot(
            [p[0] for p in pts],
            [p[1] for p in pts],
            color=AQUA,
            lw=2.0,
            zorder=4,
            solid_capstyle="round",
        )
    # harbours
    for name, (lat, lon) in HARBOURS.items():
        ax.plot(lon, lat, "o", ms=7, mfc=BLUE, mec="white", mew=1.2, zorder=6)
        ax.annotate(
            name.replace("_", " ").title(),
            (lon, lat),
            xytext=(6, 4),
            textcoords="offset points",
            color=INK,
            fontsize=9,
            fontweight="bold",
            zorder=7,
        )
    ax.plot(79.40, 9.15, "s", ms=7, mfc=BLUE, mec="white", mew=1.2, zorder=6)
    ax.annotate(
        "Gulf of Mannar test point",
        (79.40, 9.15),
        xytext=(-8, -12),
        textcoords="offset points",
        color=INK,
        fontsize=8,
        ha="right",
        zorder=7,
    )
    ax.set_xlim(65, 97.5)
    ax.set_ylim(3.5, 25)
    ax.set_aspect("equal")
    ax.grid(color=GRID, lw=0.5)
    ax.set_xlabel("longitude (°E)")
    ax.set_ylabel("latitude (°N)")
    n_pfz = len(verts)
    ax.set_title(
        f"Sagar Setu datasets on one map — INCOIS PFZ advisory ({n_pfz} lines, 14 Sep 2026), Marine Regions boundaries, test harbours",
        color=INK,
        fontsize=10,
        loc="left",
    )
    handles = [
        Line2D([0], [0], color=AQUA, lw=2, label="INCOIS Potential Fishing Zone lines"),
        Line2D(
            [0], [0], color=ORANGE, lw=1.6, ls="--", label="International maritime boundary (IMBL)"
        ),
        Line2D([0], [0], color=INK2, lw=0.8, label="Indian EEZ outer limit (200 NM)"),
        Line2D(
            [0], [0], marker="o", color="none", mfc=BLUE, mec="white", ms=7, label="Test harbour"
        ),
    ]
    ax.legend(
        handles=handles,
        loc="lower left",
        frameon=True,
        facecolor="white",
        edgecolor=GRID,
        fontsize=8,
    )
    ax.text(
        0.995,
        0.01,
        "Sources: INCOIS GeoServer WFS (pfzlines), Marine Regions v12 (VLIZ). Drawn from docs/datasets/*.csv and data/static/.",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=7,
        color=INK2,
    )
    fig.tight_layout()
    fig.savefig(D / "map_datasets.png")
    print("wrote map_datasets.png")


def plot_chl() -> None:
    cop = [
        (date.fromisoformat(r["date"]), float(r["chl_mg_m3"]))
        for r in read("copernicus_chlorophyll_kochi_2021_2026.csv")
    ]
    vii = [
        (date.fromisoformat(r["date"]), float(r["chlor_a_mg_m3"]))
        for r in read("noaa_viirs_chlorophyll.csv")
        if r["harbour"] == "kochi"
    ]
    fig, ax = plt.subplots(figsize=(11, 4), dpi=150)
    ax.set_facecolor("#fcfcfb")
    ax.plot(
        [d for d, _ in cop],
        [v for _, v in cop],
        color=BLUE,
        lw=1.0,
        label="Copernicus Marine BGC forecast/analysis, 0.25° mean (daily, Nov 2021 → Sep 2026)",
    )
    ax.plot(
        [d for d, _ in vii],
        [v for _, v in vii],
        color=ORANGE,
        lw=0,
        marker="o",
        ms=3.5,
        label="NOAA VIIRS satellite, ~4 km coastal pixel (daily, Aug–Sep 2026)",
    )
    last = cop[-1]
    ax.annotate(
        f"{last[1]:.2f} mg/m³\n{last[0]:%d %b %Y} (forecast)",
        last,
        xytext=(-70, 25),
        textcoords="offset points",
        fontsize=8,
        color=INK,
        arrowprops={"arrowstyle": "-", "color": INK2, "lw": 0.6},
    )
    ax.set_ylabel("chlorophyll-a (mg/m³)")
    ax.set_title(
        "Chlorophyll-a off Kochi (9.97 N, 76.28 E): a five-year daily baseline and a nine-day forecast — two sources, shown separately, never averaged",
        color=INK,
        fontsize=10,
        loc="left",
    )
    ax.grid(color=GRID, lw=0.5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(loc="upper left", frameon=False, fontsize=8)
    ax.text(
        0.995,
        0.01,
        "Sources: Copernicus cmems_mod_glo_bgc-pft_anfc_0.25deg_P1D-m; NOAA CoastWatch noaacwNPPN20VIIRSDINEOFDaily.",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=7,
        color=INK2,
    )
    fig.tight_layout()
    fig.savefig(D / "chlorophyll_kochi.png")
    print("wrote chlorophyll_kochi.png")


if __name__ == "__main__":
    plot_map()
    plot_chl()
