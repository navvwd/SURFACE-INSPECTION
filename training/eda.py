"""Step 4 - exploratory data analysis.

Usage:
    python -m training.eda [--config configs/data.yaml]

Requires dataset/splits/*.csv (run make_splits first). Pixel-level statistics are computed on the
TRAIN split only, so that no modelling decision is informed by validation/test images. The class
distribution figure covers all splits (counts only).

Outputs (reports/eda/):
    01_class_distribution.png  02_sample_grid.png  03_mean_images.png
    04_intensity_histograms.png  05_brightness_contrast.png  eda_summary.json
"""
import argparse

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image

from ml.utils.config import load_config, rel, resolve, write_json


def load_gray(path: str) -> np.ndarray:
    return np.asarray(Image.open(resolve(path)).convert("L"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/data.yaml")
    cfg = load_config(ap.parse_args().config)
    classes = cfg["dataset"]["classes"]
    seed = cfg["split"]["seed"]
    split_dir, out = resolve(cfg["split"]["out_dir"]), resolve(cfg["reports"]["eda_dir"])
    out.mkdir(parents=True, exist_ok=True)

    splits = {s: pd.read_csv(split_dir / f"{s}.csv") for s in ("train", "val", "test")}
    train = splits["train"]
    plt.rcParams.update({"figure.dpi": 120, "axes.spines.top": False, "axes.spines.right": False})

    # 1. class distribution per split
    counts = pd.DataFrame({s: d["label"].value_counts() for s, d in splits.items()}).reindex(classes)
    ax = counts.plot(kind="bar", figsize=(9, 4.5), color=["#2a6f97", "#61a5c2", "#a9d6e5"], width=0.8)
    ax.set_title("NEU-CLS - images per class and split")
    ax.set_ylabel("images"); ax.set_xlabel("")
    for c in ax.containers:
        ax.bar_label(c, fontsize=7)
    plt.xticks(rotation=20); plt.tight_layout(); plt.savefig(out / "01_class_distribution.png"); plt.close()

    # load train images once
    imgs = {c: np.stack([load_gray(p) for p in train.loc[train["label"] == c, "filepath"]]) for c in classes}

    # 2. sample grid (6 random train images per class, fixed seed)
    rng = np.random.default_rng(seed)
    fig, axes = plt.subplots(len(classes), 6, figsize=(10, 10.5))
    for i, c in enumerate(classes):
        for j, k in enumerate(rng.choice(len(imgs[c]), 6, replace=False)):
            a = axes[i, j]; a.imshow(imgs[c][k], cmap="gray", vmin=0, vmax=255); a.set_xticks([]); a.set_yticks([])
        axes[i, 0].set_ylabel(c, rotation=0, ha="right", va="center", fontsize=9)
    fig.suptitle("Random training samples per class (seed=%d)" % seed)
    plt.tight_layout(); plt.savefig(out / "02_sample_grid.png"); plt.close()

    # 3. mean image per class
    fig, axes = plt.subplots(1, len(classes), figsize=(14, 2.8))
    for a, c in zip(axes, classes):
        a.imshow(imgs[c].mean(axis=0), cmap="gray"); a.set_title(c, fontsize=9); a.axis("off")
    fig.suptitle("Per-class mean image (train split)")
    plt.tight_layout(); plt.savefig(out / "03_mean_images.png"); plt.close()

    # 4. intensity histograms
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for c in classes:
        h, edges = np.histogram(imgs[c].ravel(), bins=64, range=(0, 255), density=True)
        ax.plot((edges[:-1] + edges[1:]) / 2, h, label=c, lw=1.6)
    ax.set_title("Pixel intensity distribution per class (train split)")
    ax.set_xlabel("gray level"); ax.set_ylabel("density"); ax.legend(fontsize=8)
    plt.tight_layout(); plt.savefig(out / "04_intensity_histograms.png"); plt.close()

    # 5. per-image brightness (mean) and contrast (std)
    means = {c: imgs[c].reshape(len(imgs[c]), -1).mean(1) for c in classes}
    stds = {c: imgs[c].reshape(len(imgs[c]), -1).std(1) for c in classes}
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    axes[0].boxplot([means[c] for c in classes], tick_labels=classes); axes[0].set_title("Per-image brightness (mean gray)")
    axes[1].boxplot([stds[c] for c in classes], tick_labels=classes); axes[1].set_title("Per-image contrast (std gray)")
    for a in axes:
        a.tick_params(axis="x", rotation=25, labelsize=8)
    plt.tight_layout(); plt.savefig(out / "05_brightness_contrast.png"); plt.close()

    summary = {
        "note": "Pixel statistics computed on the train split only.",
        "counts_per_split": counts.to_dict(orient="index"),
        "train_per_class": {c: {
            "n": int(len(imgs[c])),
            "brightness_mean": round(float(means[c].mean()), 2), "brightness_sd": round(float(means[c].std()), 2),
            "contrast_mean": round(float(stds[c].mean()), 2), "contrast_sd": round(float(stds[c].std()), 2),
        } for c in classes},
    }
    write_json(summary, out / "eda_summary.json")
    print(pd.DataFrame(summary["train_per_class"]).T.to_string())
    print(f"\nFigures written to {rel(out)}/")


if __name__ == "__main__":
    main()
