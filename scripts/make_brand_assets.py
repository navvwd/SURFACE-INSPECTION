"""Generate website imagery from REAL model output (no stock photos, no invented results).

For each NEU-CLS class, picks one held-out TEST image that the model classifies correctly with the most
localised Grad-CAM map (an illustrative, explicitly selected example), runs the trained model + Grad-CAM, and
writes to frontend/public/brand/:
    <code>.jpg          steel surface (upscaled 2x for display)
    <code>_cam.jpg      Grad-CAM overlay from the real model
    strip.jpg           panoramic strip tiled from real NEU images (decorative texture)
    brand.json          the real predictions shown on the website (+ provenance)

Usage:  python scripts/make_brand_assets.py [--model-dir models/resnet18/v1]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from inference.gradcam import heatmap_stats, overlay  # noqa: E402
from inference.predictor import ModelBundle, prepare_image  # noqa: E402

CODES = {"Crazing": "cr", "Inclusion": "in", "Patches": "pa", "Pitted_Surface": "ps",
         "Rolled-in_Scale": "rs", "Scratches": "sc"}


def up(img: np.ndarray, size: int = 400) -> np.ndarray:
    return cv2.resize(img, (size, size), interpolation=cv2.INTER_CUBIC)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", default="models/resnet18/v1")
    ap.add_argument("--candidates", type=int, default=15)
    args = ap.parse_args()
    out = ROOT / "frontend/public/brand"
    out.mkdir(parents=True, exist_ok=True)
    bundle = ModelBundle(ROOT / args.model_dir)
    test = pd.read_csv(ROOT / "dataset/splits/test.csv")
    examples = {}
    for cls, code in CODES.items():
        best = None
        for p in test[test["label"] == cls]["filepath"].head(args.candidates):
            img = prepare_image((ROOT / p).read_bytes())
            pred = bundle.predict(img)
            if pred.predicted_class != cls:
                continue
            heat, _ = bundle.gradcam.compute(img.gray, pred.class_index)
            area = heatmap_stats(heat)["area_above_0_5"]
            if best is None or area < best[0]:
                best = (area, p, img, pred, heat)
        area, p, img, pred, heat = best
        cv2.imwrite(str(out / f"{code}.jpg"), up(img.gray), [cv2.IMWRITE_JPEG_QUALITY, 88])
        cv2.imwrite(str(out / f"{code}_cam.jpg"), up(overlay(img.gray, heat, alpha=0.5)), [cv2.IMWRITE_JPEG_QUALITY, 88])
        examples[cls] = {"code": code, "source": p, "predicted_class": pred.predicted_class,
                         "confidence": round(pred.confidence, 4), "latency_ms": pred.latency_ms,
                         "probabilities": {k: round(v, 4) for k, v in pred.probabilities.items()}}
        print(f"{cls:16s} {p}  conf={pred.confidence:.4f}  cam_area={area:.2f}")

    # decorative panoramic strip: real NEU images tiled side by side
    tiles = []
    for cls in ["Rolled-in_Scale", "Crazing", "Scratches", "Pitted_Surface", "Inclusion", "Patches"]:
        p = test[test["label"] == cls]["filepath"].iloc[20]
        tiles.append(cv2.imread(str(ROOT / p), cv2.IMREAD_GRAYSCALE))
    cv2.imwrite(str(out / "strip.jpg"), cv2.resize(np.hstack(tiles), (1800, 300), interpolation=cv2.INTER_CUBIC),
                [cv2.IMWRITE_JPEG_QUALITY, 85])

    meta = {
        "model": bundle.key,
        "note": ("Illustrative examples: real outputs of the trained model on held-out NEU-CLS test images, "
                 "selected for clearly localised Grad-CAM maps. Not a performance claim."),
        "examples": examples,
    }
    (out / "brand.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Wrote {len(examples)} examples + strip to {out}")


if __name__ == "__main__":
    main()
