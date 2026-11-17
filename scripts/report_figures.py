"""Figures for the project report (docs/report/figures/fig_*.png).

    uv run python scripts/report_figures.py

1. fig_verification.png  hit rate / false-alarm ratio / CSI of the do-not-sail verdict by
                          forecast lead (docs/evaluation.md, data/eval/backtest.json)
2. fig_cyclone_replay.png warning lead time for every harbour hit by the 4 north Indian Ocean
                          storms since mid-2025 (BUILD_LOG Step 41)
3. fig_grid_instance.png  the route search space off Rameswaram: cell classes and the A* path

Palette: the validated reference categorical slots (blue, orange, aqua) for the bars;
sequential blue for sea; values are labelled on every bar and the report carries the tables.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "docs" / "report" / "figures"

INK, INK2, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
plt.rcParams.update(
    {
        "font.family": "Arial",
        "font.size": 10,
        "axes.edgecolor": AXIS,
        "axes.labelcolor": INK2,
        "xtick.color": INK2,
        "ytick.color": INK2,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": 200,
    }
)


def verification() -> None:
    leads = ["1 day ahead", "2 days ahead", "3 days ahead"]
    series = {  # docs/evaluation.md, do-not-sail event, 460 harbour-mornings per lead
        "Hit rate (POD)": ([93.9, 97.0, 90.9], BLUE),
        "False-alarm ratio": ([3.1, 17.9, 30.2], ORANGE),
        "Critical success index": ([91.2, 80.0, 65.2], AQUA),
    }
    fig, ax = plt.subplots(figsize=(6.6, 3.3))
    x = np.arange(len(leads))
    w = 0.26
    for k, (name, (vals, color)) in enumerate(series.items()):
        bars = ax.bar(x + (k - 1) * (w + 0.015), vals, w, color=color, label=name, zorder=3)
        for b, v in zip(bars, vals, strict=True):
            ax.text(b.get_x() + b.get_width() / 2, v + 1.5, f"{v:g}", ha="center", va="bottom",
                    fontsize=8, color=INK)
    ax.set_xticks(x, leads)
    ax.set_ylim(0, 110)
    ax.set_ylabel("%")
    ax.yaxis.grid(True, color=GRID, linewidth=0.6, zorder=0)
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.13), fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "fig_verification.png", bbox_inches="tight")
    plt.close(fig)


def cyclone_replay() -> None:
    # (storm, harbour, hours from first DO NOT SAIL to the storm's closest approach)
    rows = [
        ("Ditwah", "Cuddalore", 82), ("Ditwah", "Nagapattinam", 70), ("Murasu", "Nizampatnam", 53),
        ("Ditwah", "Rameswaram", 46), ("Arnab", "Machilipatnam", 43), ("Arnab", "Kakinada", 39),
        ("Arnab", "Visakhapatnam", 34), ("Arnab", "Nizampatnam", 27), ("One", "Visakhapatnam", 24),
    ]
    fig, ax = plt.subplots(figsize=(6.6, 3.4))
    y = np.arange(len(rows))[::-1]
    bars = ax.barh(y, [r[2] for r in rows], height=0.62, color=BLUE, zorder=3)
    for b, r in zip(bars, rows, strict=True):
        ax.text(b.get_width() + 1.2, b.get_y() + b.get_height() / 2, f"{r[2]} h", va="center",
                fontsize=8, color=INK)
    ax.set_yticks(y, [f"{h}  ({s})" for s, h, _ in rows], fontsize=9)
    ax.set_xlabel("Hours of warning before the storm's closest approach")
    ax.set_xlim(0, 95)
    ax.xaxis.grid(True, color=GRID, linewidth=0.6, zorder=0)
    fig.tight_layout()
    fig.savefig(OUT / "fig_cyclone_replay.png", bbox_inches="tight")
    plt.close(fig)


def calm_sea():
    """A uniform calm sea (0.6 m, 8 s, 8 kt) on a 0.1° grid, as in tests/test_route.py, so the
    figure shows the geometry of the search, not one day's weather."""
    from marine.geo.route import SeaField

    la, lo = np.meshgrid(np.arange(8.5, 10.8, 0.1), np.arange(78.4, 80.4, 0.1), indexing="ij")
    la, lo = la.ravel(), lo.ravel()
    n = len(la)
    return SeaField(la, lo, np.full(n, 0.6), np.full(n, 8.0), np.full(n, 225.0), np.full(n, 8.0),
                    np.full(n, 225.0), np.zeros(n), np.zeros(n))


def grid_instance() -> None:
    from marine.geo.route import build_grid, plan_route, route_bbox

    start, goal = (9.29, 79.31), (9.01, 79.21)  # Rameswaram harbour -> a Gulf of Mannar point
    sea = calm_sea()
    r = plan_route(start, goal, sea)
    g = build_grid(*route_bbox(start, goal), sea)
    # classes: 0 open Indian sea, 1 land, 2 foreign waters, 3 within 2 km of the IMBL
    cls = np.zeros(g.shape, dtype=int)
    cls[g.in_eez & ~g.land & (g.imbl_km < g.margin_km)] = 3
    cls[g.foreign] = 2
    cls[g.land] = 1
    cmap = ListedColormap(["#cde2fb", "#d9d6cc", "#f6c2ae", "#eda100"])
    fig, ax = plt.subplots(figsize=(6.6, 5.0))
    lon0, lon1, lat0, lat1 = g.lons[0], g.lons[-1], g.lats[0], g.lats[-1]
    step = g.lons[1] - g.lons[0]
    ax.imshow(cls, origin="lower", cmap=cmap, vmin=-0.5, vmax=3.5, interpolation="nearest",
              extent=(lon0 - step / 2, lon1 + step / 2, lat0 - step / 2, lat1 + step / 2))
    ax.plot([start[1], goal[1]], [start[0], goal[0]], ls="--", lw=1.4, color="#e34948", zorder=4)
    ax.plot([p[1] for p in r.path], [p[0] for p in r.path], lw=2.2, color="#104281", zorder=5,
            marker="o", ms=4)
    ax.plot(start[1], start[0], "s", ms=7, color=INK, zorder=6)
    ax.plot(goal[1], goal[0], "*", ms=12, color=INK, zorder=6)
    ax.annotate("Rameswaram harbour", (start[1], start[0]), (-12, -16), textcoords="offset points",
                fontsize=8.5, color=INK, ha="right",
                bbox={"boxstyle": "round,pad=0.2", "fc": "white", "ec": "none", "alpha": 0.85})
    ax.annotate("destination", (goal[1], goal[0]), (8, -12), textcoords="offset points",
                fontsize=8.5, color=INK)
    ax.set_xlabel("Longitude (°E)")
    ax.set_ylabel("Latitude (°N)")
    ax.set_aspect(1 / np.cos(np.radians((lat0 + lat1) / 2)))
    handles = [
        Patch(color="#cde2fb", label="open Indian sea (passable)"),
        Patch(color="#d9d6cc", label="land"),
        Patch(color="#f6c2ae", label="Sri Lankan waters"),
        Patch(color="#eda100", label="within 2 km of the IMBL"),
        plt.Line2D([], [], color="#104281", lw=2.2, marker="o", ms=4,
                   label=f"A* route, {r.distance_km:g} km"),
        plt.Line2D([], [], color="#e34948", lw=1.4, ls="--", label="straight line (crosses land)"),
    ]
    ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.01, 1), frameon=False,
              fontsize=8.5)
    fig.tight_layout()
    fig.savefig(OUT / "fig_grid_instance.png", bbox_inches="tight")
    plt.close(fig)
    print(f"grid {g.shape}, {g.navigable.sum()} passable cells, route {r.distance_km} km, "
          f"{len(r.path)} waypoints, min IMBL {r.min_imbl_km} km, {r.compute_ms} ms")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    verification()
    cyclone_replay()
    grid_instance()
    print("wrote", sorted(p.name for p in OUT.glob("fig_*.png")))
