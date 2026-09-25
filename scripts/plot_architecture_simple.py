"""The simple architecture figures — the ones meant to be read in half a minute.

  architecture.png   the main diagram: what the parts are and how they connect
  flow.png           the same journey with measured timings

Deliberately sparse. Five boxes, one line of explanation each, two badges' worth of
colour. Anything that needed a third line of text belongs in the document, not the
picture. The detailed engineering diagram lives in scripts/plot_architecture.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager as fm  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from marine.config import ROOT  # noqa: E402

OUT = ROOT / "docs" / "architecture"

INK, INK2 = "#101010", "#444444"
BLUE, GREEN, RED, GREY = "#2a78d6", "#128a5c", "#c0392b", "#6b6b6b"
BLUE_BG, GREEN_BG, RED_BG, GREY_BG = "#e8f1fc", "#e6f6ee", "#fdeceb", "#f2f2f0"

_indic = [p for p in fm.findSystemFonts() if "nirmala" in p.lower()]
INDIC = fm.FontProperties(fname=_indic[0]) if _indic else None
plt.rcParams.update({"font.family": "DejaVu Sans"})


def node(ax, x, y, w, h, title, sub=None, *, fc="#ffffff", ec=GREY, lw=1.8,
         tsize=13.5, ssize=10.5, badge=None, bcol=None):
    """Title anchored to the top of the box, subtitle beneath it — never overlapping."""
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.1",
                                facecolor=fc, edgecolor=ec, linewidth=lw, zorder=2))
    if sub:
        ax.text(x + w / 2, y + h - 1.4, title, size=tsize, weight="bold", color=INK,
                ha="center", va="top", zorder=4)
        ax.text(x + w / 2, y + h - 4.6, sub, size=ssize, color=INK2,
                ha="center", va="top", zorder=4, linespacing=1.6)
    else:
        ax.text(x + w / 2, y + h / 2, title, size=tsize, weight="bold", color=INK,
                ha="center", va="center", zorder=4)
    if badge:
        bw, bh = 9.0, 2.8
        bx, by = x - bw - 1.8, y + h / 2 - bh / 2
        ax.add_patch(FancyBboxPatch((bx, by), bw, bh, boxstyle="round,pad=0,rounding_size=0.55",
                                    facecolor=bcol, edgecolor="none", zorder=5))
        ax.text(bx + bw / 2, by + bh / 2, badge, size=9, weight="bold", color="white",
                ha="center", va="center", zorder=6)


def down(ax, x, y0, y1, *, color=GREY, lw=2.2):
    ax.add_patch(FancyArrowPatch((x, y0), (x, y1), arrowstyle="-|>", mutation_scale=18,
                                 color=color, linewidth=lw, zorder=3, shrinkA=0, shrinkB=0))


def side(ax, p0, p1, *, color=GREY, lw=2.0, ls="solid", ms=15):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=ms, color=color,
                                 linewidth=lw, zorder=3, linestyle=ls, shrinkA=0, shrinkB=0))


# ---------------------------------------------------------------- main diagram

X, W = 20.0, 46.0          # the single column of steps
CX = X + W / 2             # its centre line


def architecture() -> None:
    fig, ax = plt.subplots(figsize=(10.0, 11.0), dpi=150)
    ax.set_xlim(0, 100)
    ax.set_ylim(-1, 108)
    ax.axis("off")

    ax.text(53, 106, "Sagar Setu — how the system works",
            size=19, weight="bold", ha="center", va="top", color=INK)

    # ---- the question
    ax.text(CX, 99.4, "A question, in any language", size=11, color=INK,
            ha="center", va="center", weight="bold")
    ax.text(CX, 96.4, '"Is it safe to go out tomorrow morning?"', size=10, color=INK2,
            ha="center", va="center", style="italic")
    down(ax, CX, 94.2, 90.8)

    # ---- the five steps
    node(ax, X, 80.0, W, 10.8, "1.   Understand the question",
         "Which language, which place, which day",
         fc=BLUE_BG, ec=BLUE, badge="AI", bcol=BLUE)
    down(ax, CX, 80.0, 76.6)

    node(ax, X, 63.5, W, 12.6, "2.   Collect the data",
         "Three collectors at the same time, from\nINCOIS · Open-Meteo · Copernicus · NOAA",
         fc=GREEN_BG, ec=GREEN, badge="AI", bcol=BLUE)
    down(ax, CX, 63.5, 60.4)

    # ---- the load-bearing line
    ax.plot([4, 68], [58.6, 58.6], color=RED, lw=3.0, ls=(0, (7, 5)), zorder=3)
    ax.text(CX, 56.6, "No AI below this line — only fixed rules",
            size=12, weight="bold", color=RED, ha="center", va="top")

    down(ax, CX, 52.0, 48.6)
    node(ax, X, 35.8, W, 12.8, "3.   Decide if it is safe",
         "Seven checks against a safety table.\nThe worst one decides — never an average.",
         fc=RED_BG, ec=RED, badge="NO AI", bcol=RED)

    ax.text(CX, 33.4, "GO      ·      CAUTION      ·      DO NOT SAIL",
            size=11, weight="bold", color=RED, ha="center", va="center")
    down(ax, CX, 31.4, 28.0, color=RED)

    node(ax, X, 17.2, W, 10.8, "4.   Write the answer",
         "In plain words, in the same language",
         fc=BLUE_BG, ec=BLUE, badge="AI", bcol=BLUE)
    down(ax, CX, 17.2, 13.8)

    node(ax, X, 1.0, W, 12.8, "5.   Check every number",
         "Anything not in the ledger is removed\nand the answer is written again",
         fc=RED_BG, ec=RED, badge="NO AI", bcol=RED)

    # ---- the ledger, a rail beside the whole thing
    lx, lw_ = 72.0, 25.0
    ly, lh = 1.0, 75.0
    ax.add_patch(FancyBboxPatch((lx, ly), lw_, lh, boxstyle="round,pad=0,rounding_size=1.1",
                                facecolor="#f7fbff", edgecolor=BLUE, linewidth=1.8, zorder=2))
    ax.text(lx + lw_ / 2, ly + lh / 2 + 9.0, "Evidence\nledger", size=14, weight="bold",
            color=BLUE, ha="center", va="center", linespacing=1.5, zorder=4)
    ax.text(lx + lw_ / 2, ly + lh / 2 - 6.0,
            "Every number the\nsystem finds, with\nits source and how\nfresh it is.\n\n"
            "The answer can only\nuse what is in here.",
            size=10, color=INK2, ha="center", va="center", linespacing=1.7, zorder=4)

    side(ax, (X + W, 69.8), (lx, 69.8), color=BLUE)              # written into
    side(ax, (lx, 7.4), (X + W, 7.4), color=BLUE, ls=(0, (2, 2)))  # read back from

    fig.savefig(OUT / "architecture.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote architecture.png")


# ---------------------------------------------------------------- flow

FLOW = [
    ("1", "Understand the question", "Tamil recognised; place, time and boat size picked out", "2.8 s", BLUE, "AI"),
    ("2", "Collect the data", "Sea conditions and border checks at once — 129 numbers recorded", "0.6 s", GREEN, ""),
    ("3", "Decide if it is safe", "Seven checks against the safety table  →  CAUTION", "0.0001 s", RED, "no AI"),
    ("4", "Write the answer", "Four sentences in Tamil, appearing as they are written", "4.6 s", BLUE, "AI"),
    ("5", "Check every number", "All 13 numbers traced back to the ledger — none invented", "0.0001 s", RED, "no AI"),
]


def flow() -> None:
    fig, ax = plt.subplots(figsize=(12.5, 6.8), dpi=150)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 54)
    ax.axis("off")

    ax.text(2, 51.2, "One real question, start to finish", size=15, weight="bold", ha="left", color=INK)
    ax.text(2, 47.8, "நாளை காலை இராமேஸ்வரத்தில் இருந்து 90 டிகிரி திசையில் 8 நாட் வேகத்தில் போகலாமா?",
            size=11.5, ha="left", color=INK, fontproperties=INDIC)
    ax.text(2, 44.8, "\"Can I go out from Rameswaram tomorrow morning, heading 90° at 8 knots?\"",
            size=10, ha="left", color=INK2, style="italic")

    y = 39.6
    for num, name, desc, t, col, tag in FLOW:
        h = 6.4
        ax.add_patch(FancyBboxPatch((3, y - h), 94, h, boxstyle="round,pad=0,rounding_size=0.8",
                                    facecolor="#ffffff", edgecolor="#dcdcda", linewidth=1.2, zorder=2))
        ax.add_patch(FancyBboxPatch((3, y - h), 1.0, h, boxstyle="round,pad=0,rounding_size=0.3",
                                    facecolor=col, edgecolor="none", zorder=3))
        ax.text(7.6, y - h / 2, num, size=15, weight="bold", color=col, ha="center", va="center")
        ax.text(11.8, y - 2.1, name, size=11.5, weight="bold", color=INK, ha="left", va="center")
        ax.text(11.8, y - 4.4, desc, size=9.5, color=INK2, ha="left", va="center")
        ax.text(94.5, y - h / 2, t, size=12, weight="bold", color=INK, ha="right", va="center")
        if tag:
            c = BLUE if tag == "AI" else RED
            bw = 8.8
            ax.add_patch(FancyBboxPatch((95.5 - bw - 12.5, y - h / 2 - 1.3), bw, 2.6,
                                        boxstyle="round,pad=0,rounding_size=0.55",
                                        facecolor=c, edgecolor="none", zorder=4))
            ax.text(95.5 - bw / 2 - 12.5, y - h / 2, tag, size=8.5, weight="bold",
                    color="white", ha="center", va="center", zorder=5)
        y -= 7.2

    ax.text(3, 1.8,
            "Eight seconds in all. The two AI steps take almost all of it; the safety decision itself takes a ten-thousandth of a second.",
            size=10, color=INK, ha="left")
    fig.savefig(OUT / "flow.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("wrote flow.png")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    architecture()
    flow()
