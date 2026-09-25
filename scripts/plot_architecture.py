"""Render the system architecture diagrams to docs/architecture/.

  architecture.png   layered component diagram, evidence ledger as a cross-cutting rail
  request_flow.png   what happens to one question, with measured timings

Drawn from the actual module layout in src/marine and web/src — if the code moves, this moves.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager as fm  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from marine.config import ROOT  # noqa: E402

OUT = ROOT / "docs" / "architecture"

INK, INK2, MUTED = "#0b0b0b", "#41403d", "#7a7975"
BLUE, AQUA, GREEN, ORANGE, RED, VIOLET = (
    "#2a78d6",
    "#1baf7a",
    "#0b5c3f",
    "#eb6834",
    "#c0392b",
    "#4a3aa7",
)
BURNT, GREY_BG, GREY_LINE = "#9c4318", "#f2f1ee", "#d9d8d3"

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})

# Nirmala UI carries Tamil and Devanagari; DejaVu does not.
_indic = [p for p in fm.findSystemFonts() if "nirmala" in p.lower()]
INDIC = fm.FontProperties(fname=_indic[0]) if _indic else None


def box(ax, x, y, w, h, *, fc="#ffffff", ec=GREY_LINE, lw=1.0, r=0.8, z=2, ls="solid"):
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle=f"round,pad=0,rounding_size={r}",
            facecolor=fc,
            edgecolor=ec,
            linewidth=lw,
            zorder=z,
            linestyle=ls,
        )
    )


def text(
    ax,
    x,
    y,
    s,
    *,
    size=9,
    weight="normal",
    color=INK,
    ha="center",
    va="center",
    z=5,
    style="normal",
    rotation=0,
    font=None,
):
    kw = {"fontproperties": font} if font else {}
    return ax.text(
        x,
        y,
        s,
        size=size,
        weight=weight,
        color=color,
        ha=ha,
        va=va,
        zorder=z,
        style=style,
        rotation=rotation,
        linespacing=1.45,
        **kw,
    )


def arrow(ax, p0, p1, *, color=INK2, lw=1.5, ms=11, z=4, ls="solid"):
    ax.add_patch(
        FancyArrowPatch(
            p0,
            p1,
            arrowstyle="-|>",
            mutation_scale=ms,
            color=color,
            linewidth=lw,
            zorder=z,
            linestyle=ls,
            shrinkA=1,
            shrinkB=1,
        )
    )


def band(ax, y, h, label, color, *, x=4.0, w=69.0):
    box(ax, x, y, w, h, fc=GREY_BG, ec=GREY_LINE, lw=0.8, z=1)
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            0.55,
            h,
            boxstyle="round,pad=0,rounding_size=0.25",
            facecolor=color,
            edgecolor="none",
            zorder=3,
        )
    )
    text(ax, x - 0.9, y + h / 2, label, size=8.2, weight="bold", color=color, rotation=90)


# ---------------------------------------------------------------- main diagram

RAIL_X, RAIL_W = 76.5, 21.0
UP = 71.8  # lane for the result path
BUS = 67.5  # lane for the tool-call path


def architecture() -> None:
    fig, ax = plt.subplots(figsize=(13.8, 17.0), dpi=150)
    ax.set_xlim(-1.5, 99.5)
    ax.set_ylim(3.5, 116)
    ax.axis("off")

    text(ax, 3.1, 113.4, "Sagar Setu — system architecture", size=17, weight="bold", ha="left")
    text(
        ax,
        3.1,
        111.0,
        "Conversational marine decision support for Indian small-craft fishermen · ISRO/INCOIS problem statement, SIH 2026",
        size=10,
        color=INK2,
        ha="left",
    )
    text(
        ax,
        3.1,
        109.0,
        "Eight layers. The request path runs downward, the result path upward. Every value fetched is written to the evidence ledger (right rail) before anything may use it.",
        size=8.4,
        color=MUTED,
        ha="left",
    )

    # ---- 1 client --------------------------------------------------------
    band(ax, 98.8, 8.4, "CLIENT", BLUE)
    text(
        ax,
        5.2,
        105.7,
        "1 · Presentation — React 19 + Vite + TypeScript + MapLibre GL   (web/src)",
        size=10.2,
        weight="bold",
        ha="left",
        color=BLUE,
    )
    for name, sub, x, w in [
        (
            "Chat panel",
            "question typed in any\nof 10 Indian languages;\nanswer streamed back",
            5.2,
            12.4,
        ),
        (
            "Verdict badge",
            "GO / CAUTION /\nDO NOT SAIL — taken\nfrom the engine result",
            18.4,
            12.4,
        ),
        ("Map view", "PFZ lines, EEZ, IMBL,\nvessel track, predicted\ncrossing point", 31.6, 12.4),
        (
            "Evidence ledger",
            "every number with its\nsource, validity time,\nfreshness, confidence",
            44.8,
            12.4,
        ),
        ("Agent trace", "each specialist and\nits timing, live", 58.0, 12.6),
    ]:
        box(ax, x, 99.4, w, 5.2, ec=BLUE, lw=1.1)
        text(ax, x + w / 2, 103.4, name, size=9, weight="bold", color=BLUE)
        text(ax, x + w / 2, 101.2, sub, size=7.1, color=INK2)

    # ---- 2 api -----------------------------------------------------------
    band(ax, 89.0, 8.0, "API", BLUE)
    text(
        ax,
        5.2,
        95.6,
        "2 · API — FastAPI + Server-Sent Events   (src/marine/api.py)",
        size=10.2,
        weight="bold",
        ha="left",
        color=BLUE,
    )
    for name, sub, x, w in [
        ("POST /ask", "streams: agent · chunk ·\nreset · result · done", 5.2, 18.4),
        ("GET /geo/static", "EEZ + IMBL simplified\nto 228 KB, cached", 25.0, 15.0),
        ("GET /health", "provider, snapshot age,\nthreshold tables", 41.2, 14.0),
        ("startup pre-warm", "PFZ advisory + the five\nharbours, in background", 56.4, 14.2),
    ]:
        box(ax, x, 89.8, w, 5.0, ec=BLUE, lw=1.1)
        text(ax, x + w / 2, 93.6, name, size=9, weight="bold", color=BLUE)
        text(ax, x + w / 2, 91.4, sub, size=7.1, color=INK2)

    # ---- 3 orchestration -------------------------------------------------
    band(ax, 65.5, 21.3, "ORCHESTRATION", VIOLET)
    text(
        ax,
        5.2,
        85.9,
        "3 · Orchestration — LangGraph state machine   (src/marine/graph.py)",
        size=10.2,
        weight="bold",
        ha="left",
        color=VIOLET,
    )
    text(
        ax,
        5.2,
        84.6,
        "The planner emits a typed DAG; the three specialists it selects then run concurrently in one LangGraph superstep.",
        size=8,
        color=MUTED,
        ha="left",
        style="italic",
    )

    box(ax, 5.2, 77.9, 19.4, 5.8, fc="#f1effc", ec=VIOLET, lw=1.4)
    text(ax, 14.9, 82.3, "Planner", size=9.6, weight="bold", color=VIOLET)
    text(ax, 14.9, 80.9, "the only free-form LLM step", size=7.0, color=INK2, style="italic")
    text(
        ax,
        14.9,
        79.2,
        "fast path ≈ 50 ms · LLM path ≈ 2.8 s\nemits a typed task DAG",
        size=6.9,
        color=INK2,
    )

    box(ax, 26.6, 77.9, 19.4, 5.8, ec=VIOLET, lw=1.0, ls="dashed")
    text(ax, 36.3, 82.3, "Task DAG", size=9, weight="bold", color=VIOLET)
    text(
        ax,
        36.3,
        80.0,
        "intent → which specialists run,\nwhich may run in parallel,\nwhat depends on what",
        size=6.9,
        color=INK2,
    )

    box(ax, 48.0, 77.9, 20.6, 5.8, ec=VIOLET, lw=1.0)
    text(ax, 58.3, 82.3, "8 intents", size=9, weight="bold", color=VIOLET)
    text(
        ax,
        58.3,
        80.0,
        "safety · pfz · boundary · conditions\nchlorophyll · general_knowledge\noff_topic · clarify",
        size=6.9,
        color=INK2,
    )

    for name, sub, x in [
        (
            "Ocean & Weather",
            "waves, swell, wind, gusts,\nvisibility, SST, currents;\nworst-of per parameter;\nflags source disagreement",
            5.2,
        ),
        (
            "Geospatial & Boundary",
            "point-in-polygon vs EEZ,\nnearest IMBL, PFZ bearing\nand distance, predictive\ncrossing 90 min ahead",
            27.0,
        ),
        (
            "Analytics & Causal",
            "chlorophyll vs multi-year\nbaseline (z-score, trend);\nnames a mechanism, never\nasserts causation",
            48.8,
        ),
    ]:
        box(ax, x, 68.6, 20.8, 7.8, ec=AQUA, lw=1.2)
        text(ax, x + 10.4, 75.1, name, size=9, weight="bold", color=GREEN)
        text(ax, x + 10.4, 71.9, sub, size=7.1, color=INK2)

    # ---- the load-bearing line -------------------------------------------
    ax.plot([-0.5, 99.0], [64.0, 64.0], color=RED, lw=2.0, ls=(0, (6, 3)), zorder=6)
    text(
        ax,
        37,
        62.7,
        "▲  above this line models plan and explain            ▼  below it, ordinary Python fetches and decides",
        size=8.6,
        weight="bold",
        color=RED,
    )

    # ---- 4 decision ------------------------------------------------------
    band(ax, 50.6, 10.8, "DECISION", RED)
    box(ax, 5.2, 51.6, 38.6, 8.4, fc="#fdeeec", ec=RED, lw=1.7)
    text(ax, 24.5, 58.6, "4 · Risk engine", size=11, weight="bold", color=RED)
    text(
        ax,
        24.5,
        57.1,
        "DETERMINISTIC · NO MODEL · 0.1 ms · 40 unit tests",
        size=7.4,
        color=RED,
        style="italic",
    )
    text(
        ax,
        14.3,
        54.3,
        "thresholds.py\n3 vessel classes × 7 parameters:\nwave height, wind + gusts, steepness,\nvisibility, lightning, cyclone, boundary",
        size=6.9,
        color=INK,
    )
    text(
        ax,
        34.5,
        54.3,
        "rules.py\nworst-of wins — never an average;\na missing wave or wind value can\nnever produce GO",
        size=6.9,
        color=INK,
    )

    box(ax, 46.0, 51.6, 19.0, 8.4, ec=VIOLET, lw=1.2)
    text(ax, 55.5, 58.6, "Synthesis & Verify", size=9.2, weight="bold", color=VIOLET)
    text(
        ax,
        55.5,
        55.2,
        "① brief built from the ledger\n② model drafts it in the\n    user's language\n③ verifier checks every number\n    → retry → else template",
        size=6.8,
        color=INK2,
    )

    arrow(ax, (44.0, 54.6), (45.8, 54.6), color=RED, lw=1.6, ms=10)
    text(ax, 44.9, 56.6, "verdict", size=6.0, color=RED, weight="bold", rotation=90)

    # ---- 5 tools + geo ---------------------------------------------------
    band(ax, 32.6, 17.6, "TOOLS  ·  GEO", BLUE)
    text(
        ax,
        5.2,
        49.2,
        "5 · Tool belt — 15 typed Pydantic functions   (src/marine/tools/)",
        size=10.2,
        weight="bold",
        ha="left",
        color=BLUE,
    )
    for name, sub, x in [
        (
            "ocean.py",
            "get_wave_forecast\nget_wind_forecast\nget_visibility_forecast\nget_sea_state · fan_out",
            5.2,
        ),
        ("spatial.py", "get_pfz_advisory\ncheck_position\npredict_boundary_crossing", 22.4),
        (
            "safety.py",
            "assess_sailing_risk\nsafety_briefing\ncyclone_status\nlightning_status",
            39.6,
        ),
        (
            "locations.py · windows.py",
            '1 223 landing centres, aliases,\nIndic names; "tomorrow morning"\n→ IST time window',
            56.8,
        ),
    ]:
        box(ax, x, 41.0, 16.0, 5.8, ec=BLUE, lw=1.0)
        text(ax, x + 8.0, 45.4, name, size=8.0, weight="bold", color=BLUE)
        text(ax, x + 8.0, 43.2, sub, size=6.4, color=INK2)

    text(
        ax,
        5.2,
        39.5,
        "6 · Geospatial library — pure functions, unit-tested   (src/marine/geo/)",
        size=9.4,
        weight="bold",
        ha="left",
        color=GREEN,
    )
    for name, sub, x, w in [
        (
            "geodesy.py",
            "great-circle distance, bearing,\ndestination point, local projection",
            5.2,
            19.8,
        ),
        (
            "boundaries.py",
            "EEZ point-in-polygon, nearest IMBL,\nproject heading → first crossing",
            26.2,
            22.6,
        ),
        ("pfz.py", "nearest INCOIS zone: distance,\nbearing, compass point", 50.0, 20.0),
    ]:
        box(ax, x, 33.8, w, 4.4, ec=AQUA, lw=1.0)
        text(ax, x + w / 2, 36.9, name, size=8.0, weight="bold", color=GREEN)
        text(ax, x + w / 2, 35.0, sub, size=6.6, color=INK2)

    # ---- 7 data access ---------------------------------------------------
    band(ax, 21.6, 9.6, "DATA ACCESS", ORANGE)
    text(
        ax,
        5.2,
        30.0,
        "7 · Data-access layer — one chain for every source   (src/marine/sources/base.py)",
        size=10.2,
        weight="bold",
        ha="left",
        color=BURNT,
    )
    cx = 5.2
    for i, (name, sub) in enumerate(
        [
            ("fresh cache", "within TTL\nconfidence 0.95"),
            ("live network", "2 s budget\nconfidence 1.00"),
            ("stale cache", "any age\nconfidence 0.70"),
            ("frozen snapshot", "committed demo data\nconfidence 0.50"),
        ]
    ):
        box(ax, cx, 22.6, 13.4, 5.0, fc="#ffffff" if i < 2 else "#fff6ef", ec=ORANGE, lw=1.1)
        text(ax, cx + 6.7, 26.2, name, size=8.4, weight="bold", color=BURNT)
        text(ax, cx + 6.7, 24.2, sub, size=6.8, color=INK2)
        if i:
            arrow(ax, (cx - 1.5, 25.1), (cx - 0.3, 25.1), color=ORANGE, lw=1.3, ms=8)
        cx += 14.9
    text(
        ax,
        64.6,
        26.4,
        "per-source TTL and timeout\nin-flight request de-duplication\nevery step labelled, never hidden",
        size=6.8,
        color=INK2,
        ha="left",
        va="center",
    )

    # ---- 8 sources -------------------------------------------------------
    band(ax, 7.6, 12.8, "SOURCES", ORANGE)
    text(
        ax,
        5.2,
        19.0,
        "8 · External data sources — all free, each verified live before code was written against it",
        size=10.2,
        weight="bold",
        ha="left",
        color=BURNT,
    )
    for name, sub, tag, x in [
        ("INCOIS", "Potential Fishing Zone\nadvisory (GeoServer WFS)", "live · daily", 5.2),
        (
            "Open-Meteo",
            "marine + weather forecast,\nhourly, 8 days ahead",
            "live · the floor",
            21.6,
        ),
        (
            "Copernicus Marine",
            "chlorophyll-a forecast +\n5-year daily baseline",
            "live · pre-fetched",
            38.0,
        ),
        ("NOAA CoastWatch", "VIIRS chlorophyll,\n~4 km", "live · fallback", 54.4),
    ]:
        box(ax, x, 12.6, 15.2, 5.2, ec=AQUA, lw=1.1)
        text(ax, x + 7.6, 16.4, name, size=8.4, weight="bold", color=GREEN)
        text(ax, x + 7.6, 14.7, sub, size=6.7, color=INK2)
        text(ax, x + 7.6, 13.3, tag, size=6.4, color=MUTED, style="italic")
    box(ax, 5.2, 8.4, 24.0, 3.6, ec=MUTED, lw=1.0, ls="dashed")
    text(ax, 17.2, 10.9, "Marine Regions (VLIZ)", size=8.0, weight="bold", color=INK2)
    text(
        ax,
        17.2,
        9.4,
        "EEZ polygon + 23 boundary segments\nstatic, committed to the repository",
        size=6.4,
        color=MUTED,
    )
    box(ax, 30.4, 8.4, 20.0, 3.6, fc="#f7f7f5", ec=MUTED, lw=1.0, ls="dashed")
    text(ax, 40.4, 10.9, "INCOIS ERDDAP (Argo)", size=8.0, weight="bold", color=MUTED)
    text(ax, 40.4, 9.4, "1° grid, ~6 weeks old\nweak cross-check only", size=6.4, color=MUTED)
    box(ax, 51.6, 8.4, 18.0, 3.6, fc="#fdeeec", ec=RED, lw=1.1, ls="dashed")
    text(ax, 60.6, 10.9, "IMD — BLOCKED", size=8.0, weight="bold", color=RED)
    text(
        ax,
        60.6,
        9.4,
        "cyclone + lightning: key pending;\nreported as a gap in every verdict",
        size=6.4,
        color=INK2,
    )

    # ---- right rail: LLM provider ---------------------------------------
    box(ax, RAIL_X, 85.4, RAIL_W, 11.0, fc="#f1effc", ec=VIOLET, lw=1.3, r=1.0)
    text(ax, 87.0, 94.9, "LLM PROVIDER LAYER", size=9.4, weight="bold", color=VIOLET)
    text(ax, 87.0, 93.3, "src/marine/agents/llm.py", size=7.0, color=INK2, style="italic")
    text(
        ax,
        87.0,
        89.6,
        "One interface, swapped by configuration:\nGemini (free tier, default) · Ollama\n(local, offline) · Anthropic · none\n\nUsed by exactly two steps — the planner\nand the synthesis draft. Never below the line.",
        size=6.8,
        color=INK2,
    )

    # ---- right rail: evidence ledger ------------------------------------
    box(ax, RAIL_X, 21.0, RAIL_W, 63.2, fc="#eef5fd", ec=BLUE, lw=1.7, r=1.0)
    text(ax, 87.0, 82.2, "EVIDENCE LEDGER", size=10.4, weight="bold", color=BLUE)
    text(ax, 87.0, 80.6, "src/marine/ledger.py", size=7.0, color=INK2, style="italic")
    text(
        ax,
        87.0,
        77.8,
        "Cross-cutting. Every tool writes here, and\nnothing reaches the user that is not a row in it.",
        size=7.1,
        color=INK,
    )

    box(ax, 78.2, 62.4, 17.6, 12.8, ec=BLUE, lw=1.0)
    text(ax, 87.0, 73.9, "one Observation", size=8.2, weight="bold", color=BLUE)
    text(
        ax,
        79.4,
        68.6,
        "variable      significant_wave_height\nvalue          1.02 m\nsource         open_meteo/marine\nvalid_time     17 Sep 06:00 IST\nfetched_at     2 min ago\ndistance_km    8 km to grid node\nconfidence     1.00\nprovenance     live | cache |\n                     stale_cache | snapshot",
        size=5.7,
        color=INK2,
        ha="left",
    )

    box(ax, 78.2, 53.0, 17.6, 7.8, ec=BLUE, lw=1.0)
    text(ax, 87.0, 59.4, "MissingObservation", size=8.2, weight="bold", color=BLUE)
    text(
        ax,
        87.0,
        56.1,
        'a variable we tried to get and\ncould not, with the reason — so\nthe answer can say "I could not\ncheck cyclone warnings"',
        size=6.5,
        color=INK2,
    )

    text(ax, 87.0, 50.6, "It serves three consumers:", size=7.8, weight="bold", color=BLUE)
    for i, t in enumerate(
        [
            "①  the risk engine reads the worst\n     value per parameter from it",
            "②  the brief handed to the model is\n     built only from it",
            "③  the verifier rejects any number in\n     the answer that is not in it",
        ]
    ):
        text(ax, 78.6, 47.2 - i * 5.0, t, size=6.7, color=INK2, ha="left")

    text(
        ax,
        87.0,
        30.0,
        "Provenance and confidence flow up\nfrom the data-access chain, so the\ninterface can show staleness\nwithout guessing — a value fetched\nsix hours ago and one fetched six\nminutes ago do not look alike.",
        size=6.7,
        color=INK2,
        style="italic",
    )

    # ---- right rail: evaluation -----------------------------------------
    box(ax, RAIL_X, 7.6, RAIL_W, 12.2, fc="#f2fbf7", ec=AQUA, lw=1.3, r=1.0)
    text(ax, 87.0, 18.3, "EVALUATION HARNESS", size=9.4, weight="bold", color=GREEN)
    text(ax, 87.0, 16.8, "src/marine/eval/", size=7.0, color=INK2, style="italic")
    text(
        ax,
        87.0,
        12.6,
        "backtest — the verdict from yesterday's\nforecast against the analysis of what the\nmorning brought: 460 harbour-mornings\n\nprospective log — tonight's verdict, scored\ntomorrow → hit rate, false-alarm ratio, CSI",
        size=6.6,
        color=INK2,
    )

    # ---- flow: request path down ----------------------------------------
    arrow(ax, (36.0, 99.4), (36.0, 95.0))
    arrow(ax, (36.0, 89.8), (36.0, 84.0))
    arrow(ax, (14.9, 77.9), (14.9, 76.6))
    arrow(ax, (14.9, 80.8), (26.4, 80.8), color=VIOLET, lw=1.2, ms=9)
    arrow(ax, (36.3, 77.9), (36.3, 76.6), color=VIOLET, lw=1.2, ms=9, ls="dashed")

    # specialists → bus → tool belt
    for x in (15.6, 37.4, 59.2):
        ax.plot([x, x], [68.6, 67.2], color=INK2, lw=1.4, zorder=4)
    ax.plot([15.6, BUS], [67.2, 67.2], color=INK2, lw=1.4, zorder=4)
    ax.plot([BUS, BUS], [67.2, 47.8], color=INK2, lw=1.5, zorder=4)
    text(
        ax,
        BUS + 1.3,
        59.0,
        "all data access goes through the tool belt",
        size=6.5,
        color=INK2,
        rotation=90,
    )
    ax.plot([13.2, BUS], [47.8, 47.8], color=INK2, lw=1.5, zorder=4)
    for x in (13.2, 30.4, 47.6, 64.8):
        arrow(ax, (x, 47.8), (x, 46.9))

    arrow(ax, (30.4, 41.0), (30.4, 38.3), color=AQUA, lw=1.4)
    arrow(ax, (25.6, 41.0), (25.6, 31.8))  # through the gap between the geo boxes
    arrow(ax, (36.0, 22.6), (36.0, 19.8))

    # ---- flow: result path up -------------------------------------------
    arrow(ax, (UP, 60.0), (UP, 84.0), color=VIOLET, lw=1.6)
    arrow(ax, (UP, 87.0), (UP, 94.6), color=VIOLET, lw=1.6)
    arrow(ax, (UP, 97.2), (UP, 104.2), color=VIOLET, lw=1.6)
    text(
        ax,
        UP + 2.8,
        74.0,
        "verified answer · verdict · ledger · map geometry",
        size=6.5,
        color=VIOLET,
        rotation=90,
    )

    # ---- ledger writes ---------------------------------------------------
    for y in (72.0, 44.0, 25.1):
        arrow(ax, (73.2, y), (76.3, y), color=BLUE, lw=1.3, ms=9, ls=(0, (2, 2)))
    text(ax, 74.8, 47.4, "writes", size=6.4, color=BLUE, rotation=90)

    # ---- legend ----------------------------------------------------------
    ax.legend(
        handles=[
            Line2D([0], [0], color=INK2, lw=1.5, label="request path (downward)"),
            Line2D([0], [0], color=VIOLET, lw=1.6, label="result path (upward)"),
            Line2D(
                [0], [0], color=BLUE, lw=1.3, ls=(0, (2, 2)), label="writes to the evidence ledger"
            ),
            Line2D(
                [0],
                [0],
                color=RED,
                lw=2.0,
                ls=(0, (6, 3)),
                label="the load-bearing line — no model below it",
            ),
        ],
        loc="lower left",
        bbox_to_anchor=(0.035, -0.012),
        frameon=True,
        facecolor="white",
        edgecolor=GREY_LINE,
        fontsize=7.4,
        ncol=2,
    )
    text(
        ax,
        98.6,
        5.0,
        "4 748 lines of Python · 629 of TypeScript · 115 tests, none needing the network or a model",
        size=7.0,
        color=MUTED,
        ha="right",
    )

    fig.savefig(OUT / "architecture.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote architecture.png")


# ---------------------------------------------------------------- request flow

STEPS = [
    (
        "1",
        "Planner",
        "Tamil detected. One model call returns the language, an English translation,\nintent = safety, the place, the time window, vessel class, heading 90°, speed 8 kt.\nAn English question takes a deterministic path instead and skips this call entirely.",
        "2.8 s",
        VIOLET,
        "model",
    ),
    (
        "2",
        "Task DAG",
        "intent = safety → Ocean & Weather and Geospatial & Boundary run\nin parallel, then the risk engine, then synthesis.",
        "< 1 ms",
        VIOLET,
        "code",
    ),
    (
        "3",
        "Specialists, in parallel",
        "Ocean: 13 variables across 05:00–12:00 IST, worst-of each. Geospatial: position\nagainst the EEZ, nearest boundary 23.1 km E, heading projected forward → crosses\nin 94.5 min.   →   129 observations written to the evidence ledger.",
        "0.6 s",
        AQUA,
        "code",
    ),
    (
        "4",
        "Risk engine",
        "Seven parameters graded against the traditional-craft table;\nworst-of wins → CAUTION (steepness 0.0433 m/s², convective\nproxy, crossing inside twice the 90 min horizon).",
        "0.14 ms",
        RED,
        "code · no model",
    ),
    (
        "5",
        "Brief",
        "One page assembled only from the ledger: verdict, reasons, worst\nvalues with provenance, gaps, degradation. This is the whole of\nwhat the model is shown about the data.",
        "< 1 ms",
        VIOLET,
        "code",
    ),
    (
        "6",
        "Synthesis",
        "The model writes four sentences in Tamil, streamed to the screen\nas they are produced. It may not compute, convert or soften\nanything it is given.",
        "4.6 s",
        VIOLET,
        "model",
    ),
    (
        "7",
        "Verifier",
        "Every number in the Tamil text — Latin and Tamil digits alike —\nmust exist in the ledger. Unsupported → one corrective retry →\nfailing that, the deterministic template ships instead.",
        "< 1 ms",
        RED,
        "code",
    ),
    (
        "8",
        "Client",
        "Verdict badge from the engine, the answer text, the map with track\nand crossing point, the ledger with freshness chips.",
        "streamed",
        BLUE,
        "code",
    ),
]


def request_flow() -> None:
    fig, ax = plt.subplots(figsize=(14, 9.6), dpi=150)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 64)
    ax.axis("off")

    text(ax, 2.0, 61.4, "What happens to one question", size=15.5, weight="bold", ha="left")
    text(
        ax,
        2.0,
        59.0,
        "நாளை காலை இராமேஸ்வரத்தில் இருந்து 90 டிகிரி திசையில் 8 நாட் வேகத்தில் போகலாமா?",
        size=11,
        color=INK,
        ha="left",
        font=INDIC,
    )
    text(
        ax,
        2.0,
        56.8,
        '"Can I go out from Rameswaram tomorrow morning on a heading of 90° at 8 knots?"   —   measured on a warm cache, 22 Sep 2026',
        size=8.6,
        color=INK2,
        ha="left",
        style="italic",
    )

    y = 54.0
    for num, name, desc, ms, col, kind in STEPS:
        h = 6.0
        box(ax, 4.0, y - h, 92.0, h, ec=GREY_LINE, lw=0.9)
        ax.add_patch(
            FancyBboxPatch(
                (4.0, y - h),
                0.5,
                h,
                boxstyle="round,pad=0,rounding_size=0.2",
                facecolor=col,
                edgecolor="none",
                zorder=3,
            )
        )
        ax.add_patch(Circle((7.6, y - 1.6), 1.3, facecolor=col, edgecolor="none", zorder=4))
        text(ax, 7.6, y - 1.6, num, size=9.2, weight="bold", color="white")
        text(ax, 10.6, y - 1.4, name, size=9.6, weight="bold", color=col, ha="left")
        text(ax, 10.6, y - 2.4, desc, size=6.8, color=INK2, ha="left", va="top")
        text(ax, 94.4, y - 1.4, ms, size=9.2, weight="bold", color=INK, ha="right")
        bc = RED if "no model" in kind else (VIOLET if kind == "model" else MUTED)
        bg = "#fdeeec" if "no model" in kind else ("#f1effc" if kind == "model" else "#f2f1ee")
        box(ax, 83.6, y - 4.3, 11.6, 1.8, fc=bg, ec=bc, lw=0.8, r=0.5)
        text(ax, 89.4, y - 3.4, kind, size=6.6, color=bc, weight="bold")
        if num != "8":
            arrow(ax, (7.6, y - h), (7.6, y - h - 0.35), color=MUTED, lw=1.2, ms=8)
        y -= 6.3

    text(
        ax,
        4.0,
        1.6,
        "Total 7.9 s end to end. The two model calls account for 7.4 s of it; everything the verdict actually depends on takes under a second. "
        "With no model configured, the same pipeline answers in English from deterministic templates in about 0.4 s.",
        size=8.0,
        color=INK2,
        ha="left",
    )
    fig.savefig(OUT / "request_flow.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote request_flow.png")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    architecture()
    request_flow()
