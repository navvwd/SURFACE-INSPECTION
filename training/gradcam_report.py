"""Grad-CAM example figure + model-randomisation sanity check.

Usage:
    python -m training.gradcam_report --model-dir models/custom_cnn/v1

1. Figure: for every class, 3 test images (seeded choice) with original / Grad-CAM overlay,
   predicted class and confidence. Wrong predictions are marked.
2. Sanity check (Adebayo et al., 2018, "Sanity Checks for Saliency Maps"): Grad-CAM maps from the
   trained model are compared with maps from the same architecture with RANDOM weights. If they were
   similar, the heatmap would reflect image structure rather than what the model learned. We report
   the mean Spearman rank correlation between the two (low = passes).

Outputs: reports/<name>_<version>/gradcam_examples.png, <model-dir>/gradcam_sanity.json
"""
from __future__ import annotations

import os

os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "1")

import argparse
import json

import keras
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
from scipy.stats import spearmanr

from inference.gradcam import CAVEAT, GradCAM, overlay
from ml.models import build_model
from ml.utils.config import load_config, rel, resolve, write_json
from ml.utils.seed import set_global_seed


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--per-class", type=int, default=3)
    ap.add_argument("--sanity-n", type=int, default=60)
    args = ap.parse_args()
    mdir = resolve(args.model_dir)
    meta = json.loads((mdir / "train_meta.json").read_text())
    cfg = load_config(mdir / "config.yaml")
    classes, seed = meta["classes"], meta["seed"]
    set_global_seed(seed)
    model = keras.models.load_model(mdir / "model.keras")
    cam = GradCAM(model, meta["gradcam_layer"])
    test = pd.read_csv(resolve(load_config(mdir / "data_config.yaml")["split"]["out_dir"]) / "test.csv")
    rng = np.random.default_rng(seed)

    # 1. example grid
    k = args.per_class
    fig, axes = plt.subplots(len(classes), 2 * k, figsize=(2.1 * 2 * k, 2.3 * len(classes)))
    for r, c in enumerate(classes):
        rows = test[test["label"] == c]
        for j, idx in enumerate(rng.choice(len(rows), k, replace=False)):
            g = np.asarray(Image.open(resolve(rows.iloc[idx]["filepath"])).convert("L"))
            probs = model(g.astype("float32")[None, ..., None], training=False).numpy()[0]
            pi = int(probs.argmax())
            heat, _ = cam.compute(g, pi)
            a0, a1 = axes[r, 2 * j], axes[r, 2 * j + 1]
            a0.imshow(g, cmap="gray", vmin=0, vmax=255)
            a1.imshow(overlay(g, heat)[..., ::-1])
            ok = classes[pi] == c
            a1.set_title(f"{'' if ok else 'WRONG: '}{classes[pi]} {probs[pi]:.2f}", fontsize=7,
                         color="#1b5e20" if ok else "#b71c1c")
            for a in (a0, a1):
                a.set_xticks([]); a.set_yticks([])
        axes[r, 0].set_ylabel(c, fontsize=8)
    fig.suptitle(f"{meta['model_name']} {meta['model_version']} - Grad-CAM on held-out test images "
                 f"(layer {meta['gradcam_layer']})\n{CAVEAT}", fontsize=8)
    plt.tight_layout()
    out_png = resolve(f"reports/{meta['model_name']}_{meta['model_version']}/gradcam_examples.png")
    plt.savefig(out_png); plt.close(fig)

    # 2. randomisation sanity check
    rand_model = build_model(cfg["model"] | {"pretrained_weights": None}, len(classes), meta["normalization_train_only"])
    rand_cam = GradCAM(rand_model, meta["gradcam_layer"])
    sample = test.iloc[rng.choice(len(test), min(args.sanity_n, len(test)), replace=False)]
    rhos, self_rhos = [], []
    for p in sample["filepath"]:
        g = np.asarray(Image.open(resolve(p)).convert("L"))
        h_trained, ci = cam.compute(g)
        h_random, _ = rand_cam.compute(g, ci)
        if h_trained.std() > 0 and h_random.std() > 0:
            rhos.append(spearmanr(h_trained.ravel()[::7], h_random.ravel()[::7]).statistic)
        # stability: same image horizontally flipped, map flipped back (should stay similar)
        h_flip, _ = cam.compute(g[:, ::-1].copy(), ci)
        if h_trained.std() > 0 and h_flip.std() > 0:
            self_rhos.append(spearmanr(h_trained.ravel()[::7], h_flip[:, ::-1].ravel()[::7]).statistic)
    res = {
        "n_images": int(len(sample)),
        "trained_vs_random_weights_spearman_mean": float(np.nanmean(rhos)),
        "trained_vs_random_weights_spearman_abs_mean": float(np.nanmean(np.abs(rhos))),
        "flip_consistency_spearman_mean": float(np.nanmean(self_rhos)),
        "interpretation": ("Low |rho| vs random weights means the maps depend on learned parameters (passes the "
                           "randomisation sanity check). High flip consistency means explanations are stable under "
                           "a label-preserving transform. Neither validates the maps as defect boundaries."),
    }
    write_json(res, mdir / "gradcam_sanity.json")
    print(json.dumps(res, indent=2))
    print(f"Saved {rel(out_png)}")


if __name__ == "__main__":
    main()
