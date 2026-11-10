"""Shared plotting helpers (matplotlib, headless)."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams.update({"figure.dpi": 120, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": 0.25})


def plot_training_curves(hist: pd.DataFrame, path, title: str) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    for ax, metric, label in [(axes[0], "loss", "Loss"), (axes[1], "accuracy", "Accuracy")]:
        ax.plot(hist["epoch"], hist[metric], label="train", color="#2a6f97", lw=1.8)
        ax.plot(hist["epoch"], hist[f"val_{metric}"], label="validation", color="#e07a1f", lw=1.8)
        boundaries = hist.groupby("stage", sort=False)["epoch"].min().iloc[1:]
        for stage, ep in boundaries.items():
            ax.axvline(ep - 0.5, color="#888", ls="--", lw=1)
            ax.text(ep - 0.3, ax.get_ylim()[1], f" {stage}", va="top", fontsize=8, color="#555")
        ax.set_title(label); ax.set_xlabel("epoch"); ax.legend()
    fig.suptitle(f"Training curves - {title} (train metrics include augmentation + dropout)")
    plt.tight_layout(); plt.savefig(path); plt.close(fig)


def plot_confusion_matrix(cm: np.ndarray, classes: list[str], path, title: str) -> None:
    norm = cm / cm.sum(axis=1, keepdims=True)
    fig, ax = plt.subplots(figsize=(7.2, 6.2))
    im = ax.imshow(norm, cmap="Blues", vmin=0, vmax=1)
    for i in range(len(classes)):
        for j in range(len(classes)):
            ax.text(j, i, f"{cm[i, j]}\n{norm[i, j]:.0%}", ha="center", va="center", fontsize=8,
                    color="white" if norm[i, j] > 0.6 else "#222")
    ax.set_xticks(range(len(classes)), classes, rotation=30, ha="right")
    ax.set_yticks(range(len(classes)), classes)
    ax.set_xlabel("Predicted"); ax.set_ylabel("True"); ax.set_title(title); ax.grid(False)
    fig.colorbar(im, fraction=0.046, pad=0.04, label="row-normalised recall")
    plt.tight_layout(); plt.savefig(path); plt.close(fig)


def plot_per_class_bars(per_class: dict, classes: list[str], path, title: str) -> None:
    metrics = ["precision", "recall", "f1"]
    x = np.arange(len(classes)); w = 0.26
    fig, ax = plt.subplots(figsize=(10, 4.2))
    for k, (m, c) in enumerate(zip(metrics, ["#2a6f97", "#61a5c2", "#e07a1f"])):
        vals = [per_class[cl][m] for cl in classes]
        ax.bar(x + (k - 1) * w, vals, w, label=m, color=c)
    lo = min(per_class[cl][m] for cl in classes for m in metrics)
    ax.set_ylim(max(0, lo - 0.1), 1.005)
    ax.set_xticks(x, classes, rotation=15); ax.set_title(title); ax.legend(loc="lower right")
    plt.tight_layout(); plt.savefig(path); plt.close(fig)
