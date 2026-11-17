"""Full-resolution screenshots of the running app for the project report.

Needs the API (port 8000) and the web app (port 5173) running. Uses the Microsoft Edge that
ships with Windows through Playwright, so no browser download is needed:

    uv run --with playwright python scripts/report_screenshots.py

Writes docs/report/figures/screen_*.png.
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "report" / "figures"
URL = "http://localhost:5173"

SHOTS = [
    ("screen_kochi_safety", "Is it safe to go out from Kochi tomorrow morning?"),
    ("screen_tamil", "நாளை காலை இராமேஸ்வரத்தில் இருந்து 90 டிகிரி திசையில் 8 நாட் வேகத்தில் போகலாமா?"),
    ("screen_border", "How far is the Sri Lanka border from Rameswaram if I head 90 at 8 knots?"),
    ("screen_route", "What is the best route from Kochi to the fishing zone?"),
    ("screen_hindi", "क्या कल सुबह वेरावल से समुद्र में जाना सुरक्षित है?"),
]


def ask(page, question: str) -> None:
    page.goto(URL)
    page.wait_for_selector("input")
    page.fill("input", question)
    page.keyboard.press("Enter")
    page.wait_for_selector(".a.final", timeout=90_000)
    page.wait_for_timeout(3_000)  # map tiles and layers


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    only = set(sys.argv[1:])
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge")
        page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1.5)
        for name, q in SHOTS:
            if only and name not in only:
                continue
            ask(page, q)
            page.screenshot(path=OUT / f"{name}.png")
            print("wrote", name)
        if not only or "screen_bank" in only:
            page.goto(URL)
            page.click("button.bank-open")
            page.wait_for_timeout(1_500)
            page.screenshot(path=OUT / "screen_bank.png")
            print("wrote screen_bank")
        browser.close()


if __name__ == "__main__":
    main()
