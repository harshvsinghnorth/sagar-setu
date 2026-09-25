"""The simple architecture figures — the ones meant to be read in half a minute.

  architecture.png   the main diagram: what the parts are and how they connect
  flow.png           the same journey with measured timings

The detailed engineering diagram lives in scripts/plot_architecture.py.
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


def node(ax, x, y, w, h, title, sub=None, *, fc="#ffffff", ec=GREY, lw=1.6,
         tsize=12.5, ssize=9.5, badge=None, bcol=None):
    """Title anchored to the top of the box, subtitle beneath it — never overlapping."""
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.1",
                                facecolor=fc, edgecolor=ec, linewidth=lw, zorder=2))
    if sub:
        ax.text(x + w / 2, y + h - 1.3, title, size=tsize, weight="bold", color=INK,
                ha="center", va="top", zorder=4)
        ax.text(x + w / 2, y + h - 4.2, sub, size=ssize, color=INK2,
                ha="center", va="top", zorder=4, linespacing=1.55)
    else:
        ax.text(x + w / 2, y + h / 2, title, size=tsize, weight="bold", color=INK,
                ha="center", va="center", zorder=4)
    if badge:
        bw, bh = 8.8, 2.6
        bx, by = x - bw - 1.6, y + h / 2 - bh / 2
        ax.add_patch(FancyBboxPatch((bx, by), bw, bh, boxstyle="round,pad=0,rounding_size=0.55",
                                    facecolor=bcol, edgecolor="none", zorder=5))
        ax.text(bx + bw / 2, by + bh / 2, badge, size=8.5, weight="bold", color="white",
                ha="center", va="center", zorder=6)


def down(ax, x, y0, y1, *, color=GREY, lw=2.2):
    ax.add_patch(FancyArrowPatch((x, y0), (x, y1), arrowstyle="-|>", mutation_scale=18,
                                 color=color, linewidth=lw, zorder=3, shrinkA=0, shrinkB=0))


def side(ax, p0, p1, *, color=GREY, lw=2.0, ls="solid", ms=15):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=ms, color=color,
                                 linewidth=lw, zorder=3, linestyle=ls, shrinkA=0, shrinkB=0))


# ---------------------------------------------------------------- main diagram

def architecture() -> None:
    fig, ax = plt.subplots(figsize=(11.5, 14.2), dpi=150)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 124)
    ax.axis("off")

    ax.text(50, 120.5, "Sagar Setu — how the system works", size=19, weight="bold",
            ha="center", color=INK)
    ax.text(50, 117.0, "A fisherman asks in his own language. The answer comes back in it, with a map.",
            size=11, ha="center", color=INK2)

    L, W = 27.0, 46.0        # centre column
    CX = L + W / 2           # 50

    node(ax, L + 4, 106.0, W - 8, 7.5, "A question, in any language",
         "\"Is it safe to go out tomorrow morning?\"",
         fc=GREY_BG, ec=GREY, lw=1.4, tsize=12, ssize=9.5)
    down(ax, CX, 106.0, 102.9)

    node(ax, L, 93.0, W, 9.5, "1.  Understand the question",
         "Works out the language, the place, the time,\nand what needs to be looked up",
         fc=BLUE_BG, ec=BLUE, lw=1.9, badge="AI", bcol=BLUE)
    down(ax, CX, 93.0, 89.4)

    node(ax, L, 77.0, W, 12.0, "2.  Collect the data",
         "Three collectors work at the same time:\nsea conditions  ·  maps and borders\nfish and plankton",
         fc=GREEN_BG, ec=GREEN, lw=1.9)

    node(ax, 1.5, 77.0, 21.0, 12.0, "Data sources",
         "INCOIS · Open-Meteo\nCopernicus · NOAA\nMarine Regions",
         fc="#ffffff", ec=GREEN, lw=1.5, tsize=11, ssize=9)
    side(ax, (22.8, 83.0), (26.6, 83.0), color=GREEN)

    down(ax, CX, 77.0, 74.0)

    # the one idea — the line stops short of the ledger
    ax.plot([6, 74], [72.8, 72.8], color=RED, lw=2.4, ls=(0, (7, 4)), zorder=6)
    ax.text(40, 70.2, "Below this line there is no AI — only fixed rules",
            size=11.5, weight="bold", color=RED, ha="center")
    down(ax, CX, 68.4, 65.8)

    node(ax, L, 53.4, W, 12.0, "3.  Decide if it is safe",
         "Checks seven things — waves, wind, visibility and so on —\nagainst a published safety table.\nThe worst one decides. Never an average.",
         fc=RED_BG, ec=RED, lw=2.1, badge="NO AI", bcol=RED)
    ax.text(CX, 50.8, "GO      ·      CAUTION      ·      DO NOT SAIL",
            size=12, weight="bold", color=RED, ha="center", va="center")
    down(ax, CX, 49.0, 46.4, color=RED)

    node(ax, L, 36.5, W, 9.5, "4.  Write the answer",
         "Puts the decision into plain words,\nin the fisherman's own language",
         fc=BLUE_BG, ec=BLUE, lw=1.9, badge="AI", bcol=BLUE)
    down(ax, CX, 36.5, 33.9)

    node(ax, L, 24.0, W, 9.5, "5.  Check every number",
         "Any number not in the ledger is thrown out\nand the answer is written again",
         fc=RED_BG, ec=RED, lw=1.9, badge="NO AI", bcol=RED)
    down(ax, CX, 24.0, 21.4)

    node(ax, L + 4, 11.5, W - 8, 9.5, "The answer, on screen",
         "In the same language, with a map\nand the evidence underneath",
         fc=GREY_BG, ec=GREY, lw=1.4, tsize=12, ssize=9.5)

    # ---- the evidence ledger, to the right --------------------------------
    LX, LW, LY, LH = 76.5, 22.0, 24.0, 65.0
    node(ax, LX, LY, LW, LH, "", None, fc=BLUE_BG, ec=BLUE, lw=1.9)
    cx = LX + LW / 2
    ax.text(cx, 84.5, "Evidence ledger", size=13, weight="bold", color=BLUE, ha="center")
    ax.text(cx, 79.5, "Every number the system\nfinds is written down here:",
            size=9.5, color=INK2, ha="center", va="top", linespacing=1.55)
    ax.text(LX + 2.6, 72.0, "·  where it came from\n·  what time it is for\n·  how fresh it is",
            size=9.5, color=INK2, ha="left", va="top", linespacing=1.75)
    ax.text(cx, 60.0, "Nothing can be shown\nto the fisherman unless\nit is in here.",
            size=10, color=INK, ha="center", va="top", linespacing=1.6, style="italic")
    ax.text(cx, 47.0, "Steps 3, 4 and 5\nall read from it.",
            size=9.5, color=INK2, ha="center", va="top", linespacing=1.6)
    ax.text(cx, 36.0, "A typical question\nrecords about\n130 numbers.",
            size=9.5, color=INK2, ha="center", va="top", linespacing=1.6)

    side(ax, (73.4, 83.0), (76.3, 83.0), color=BLUE)           # collectors write into it
    for y in (59.4, 41.25, 28.75):                             # steps 3, 4, 5 read from it
        side(ax, (76.3, y), (73.4, y), color=BLUE, lw=1.5, ls=(0, (2.5, 2.5)), ms=12)

    ax.text(50, 4.0,
            "The AI understands the question and explains the answer. It never decides whether it is safe to go to sea —\n"
            "that decision is made by fixed rules, so anyone can check it.",
            size=10.5, color=INK, ha="center", va="bottom", linespacing=1.7, weight="bold")

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
