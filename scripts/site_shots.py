"""Screenshot the marketing site at desktop / tablet / mobile widths and report browser errors + horizontal overflow.
Usage: python scripts/site_shots.py [--base http://127.0.0.1:8000]"""
import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parents[1] / "reports" / "screenshots"
ap = argparse.ArgumentParser(); ap.add_argument("--base", default="http://127.0.0.1:8000"); args = ap.parse_args()
OUT.mkdir(parents=True, exist_ok=True)
problems = []
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, w, h in [("site_desktop", 1440, 900), ("site_tablet", 820, 1100), ("site_mobile", 390, 844)]:
        pg = b.new_page(viewport={"width": w, "height": h})
        pg.on("pageerror", lambda e, n=name: problems.append(f"{n}: {e}"))
        pg.on("console", lambda m, n=name: m.type == "error" and problems.append(f"{n} console: {m.text}"))
        pg.goto(args.base + "/", wait_until="networkidle")
        pg.wait_for_timeout(2500)
        pg.screenshot(path=str(OUT / f"{name}_hero.png"))
        overflow = pg.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        if overflow > 0:
            problems.append(f"{name}: horizontal overflow {overflow}px")
        full = pg.evaluate("document.documentElement.scrollHeight")
        pg.set_viewport_size({"width": w, "height": full})
        pg.wait_for_timeout(3000)
        pg.screenshot(path=str(OUT / f"{name}_full.png"))
        print(name, "height", full, "overflow", overflow)
        pg.close()
    b.close()
print("PROBLEMS:\n  " + "\n  ".join(problems) if problems else "no browser errors, no horizontal overflow")
sys.exit(1 if problems else 0)
