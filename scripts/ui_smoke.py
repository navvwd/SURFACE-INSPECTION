"""Browser smoke test of the React dashboard against the running backend (dev tool; needs `pip install playwright`
and `python -m playwright install chromium`).

Usage (backend on :8000 and `npm run dev` on :5173 must be running):
    python scripts/ui_smoke.py [--base http://localhost:5173] [--sim-images 12]

Drives the real UI: single-image inspection, simulated production line (SSE), history + human review, and every
page. Saves screenshots to reports/screenshots/ and exits non-zero on any browser console error or failed step.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SHOTS = ROOT / "reports" / "screenshots"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:5173")
    ap.add_argument("--sim-images", type=int, default=12)
    args = ap.parse_args()
    SHOTS.mkdir(parents=True, exist_ok=True)
    test_img = ROOT / pd.read_csv(ROOT / "dataset/splits/test.csv").query("label == 'Scratches'").iloc[0]["filepath"]
    errors: list[str] = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("console", lambda m: m.type == "error" and errors.append(f"console: {m.text}"))
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))

        def shot(name):
            # A full_page capture resizes the viewport, which makes Recharts' ResponsiveContainer re-measure and
            # restart its draw-in animation mid-capture. Grow the viewport to the page height first, let the
            # charts settle, capture, then restore the normal viewport.
            page.wait_for_timeout(500)
            h = page.evaluate("document.documentElement.scrollHeight")
            page.set_viewport_size({"width": 1440, "height": max(1000, h)})
            page.wait_for_timeout(2500)
            page.screenshot(path=str(SHOTS / f"{name}.png"))
            page.set_viewport_size({"width": 1440, "height": 1000})
            print("screenshot", name)

        # 2. single-image inspection
        page.goto(f"{args.base}/app/inspect")
        page.set_input_files("input[type=file]", str(test_img))
        page.get_by_placeholder("e.g. COIL-24-0815").fill("COIL-UI-0001")
        page.get_by_placeholder("e.g. HR-LINE2-SHIFT-A").fill("UI-SMOKE")
        page.get_by_role("button", name="Run inspection").click()
        expect(page.get_by_text("Grad-CAM heatmap · layer")).to_be_visible(timeout=60000)
        expect(page.get_by_text("Inspection record")).to_be_visible()
        shot("02_image_inspection")

        # 3. simulated production line via SSE
        page.goto(f"{args.base}/app/batch")
        page.get_by_label("Images (1–270)").fill(str(args.sim_images))
        page.get_by_label("Pacing between images (ms)").fill("150")
        page.get_by_role("button", name="Start line").click()
        expect(page.get_by_text("Batch summary (from server)")).to_be_visible(timeout=180000)
        rows = page.locator("table tbody tr").count()
        if rows < args.sim_images:
            errors.append(f"batch table shows {rows} rows, expected {args.sim_images}")
        shot("03_batch_simulation")

        # 5. history + review
        page.goto(f"{args.base}/app/history")
        page.locator("tr.clickable").first.click()
        expect(page.get_by_role("dialog")).to_be_visible()
        page.get_by_placeholder("name / badge").fill("QA-Inspector-1")
        page.get_by_role("button", name="Record review").click()
        expect(page.get_by_role("dialog").get_by_text("QA-Inspector-1")).to_be_visible(timeout=20000)
        shot("05_history_review")
        page.get_by_role("button", name="Close").click()

        # remaining pages
        for path, name, marker in [("/app", "01_factory_overview", "Most recent inspections"),
                                   ("/app/analytics", "04_defect_analytics", "Predicted defect × inspection decision"),
                                   ("/app/models", "06_model_performance", "Model detail"),
                                   ("/app/reports", "07_reports", "Batch reports → PDF")]:
            page.goto(f"{args.base}{path}")
            expect(page.get_by_text(marker)).to_be_visible(timeout=30000)
            shot(name)

        # exports reachable from the UI
        for href in [page.locator("a", has_text="PDF").first.get_attribute("href"), "/api/reports/inspections.csv"]:
            r = page.request.get(f"{args.base}{href}")
            if r.status != 200:
                errors.append(f"{href} -> HTTP {r.status}")
        browser.close()

    if errors:
        print("FAILURES:\n  " + "\n  ".join(errors))
        return 1
    print("UI smoke test passed: no console errors, all steps completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
