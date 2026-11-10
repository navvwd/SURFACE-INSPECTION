"""Evaluate a trained model on the held-out TEST split (and report validation metrics alongside).

Usage:
    python -m training.evaluate --model-dir models/custom_cnn/v1

Writes <model-dir>/evaluation.json and reports/<name>_<version>/:
    confusion_matrix_test.png, per_class_test.png, misclassified_test.csv, robustness.png

The test split is used for nothing else in this project (no tuning, no early stopping).
"""
from __future__ import annotations

import os

os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "1")

import argparse
import json
import platform
from datetime import datetime, timezone

import keras
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import tensorflow as tf

from ml.data.pipeline import make_dataset, read_manifest
from ml.evaluation.latency import benchmark
from ml.evaluation.metrics import classification_metrics
from ml.utils.config import load_config, rel, resolve, write_json
from ml.utils.plots import plot_confusion_matrix, plot_per_class_bars
from ml.utils.seed import set_global_seed


def predict_probs(model, ds) -> tuple[np.ndarray, np.ndarray]:
    ys, ps = [], []
    for x, y in ds:
        ps.append(model(x, training=False).numpy())
        ys.append(y.numpy())
    return np.concatenate(ys), np.concatenate(ps)


def robustness(model, ds, classes) -> list[dict]:
    """Accuracy under synthetic global brightness / contrast changes (simulated lighting drift).
    Training augmentation covered brightness +/-38 gray levels and contrast x0.7-1.3."""
    xs, ys = zip(*[(x.numpy(), y.numpy()) for x, y in ds])
    X, Y = np.concatenate(xs), np.concatenate(ys)
    rows = []
    for kind, values in [("brightness_shift", [-80, -60, -40, -20, 0, 20, 40, 60, 80]),
                         ("contrast_scale", [0.4, 0.55, 0.7, 1.0, 1.3, 1.6, 2.0])]:
        for v in values:
            if kind == "brightness_shift":
                Xt = np.clip(X + v, 0, 255)
            else:
                m = X.mean(axis=(1, 2, 3), keepdims=True)
                Xt = np.clip((X - m) * v + m, 0, 255)
            pred = np.concatenate([model(Xt[i:i + 64], training=False).numpy().argmax(1)
                                   for i in range(0, len(Xt), 64)])
            rows.append({"perturbation": kind, "value": v, "accuracy": float((pred == Y).mean())})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", required=True)
    args = ap.parse_args()
    mdir = resolve(args.model_dir)
    meta = json.loads((mdir / "train_meta.json").read_text())
    tcfg = load_config(mdir / "config.yaml")
    dcfg = load_config(mdir / "data_config.yaml")
    classes = meta["classes"]
    seed = meta["seed"]
    set_global_seed(seed)
    rdir = resolve(f"reports/{meta['model_name']}_{meta['model_version']}")
    rdir.mkdir(parents=True, exist_ok=True)

    model = keras.models.load_model(mdir / "model.keras")
    split_dir = dcfg["split"]["out_dir"]
    bs = tcfg["data"]["batch_size"]
    test_df = read_manifest(split_dir, "test")
    results = {}
    for split in ("val", "test"):
        df = test_df if split == "test" else read_manifest(split_dir, split)
        y, p = predict_probs(model, make_dataset(df, bs, training=False, seed=seed))
        pred = p.argmax(1)
        m = classification_metrics(y, pred, classes)
        conf = p.max(1)
        m["mean_confidence_correct"] = float(conf[pred == y].mean()) if (pred == y).any() else None
        m["mean_confidence_wrong"] = float(conf[pred != y].mean()) if (pred != y).any() else None
        results[split] = m
        if split == "test":
            test_probs, test_pred, test_y = p, pred, y

    cm = np.array(results["test"]["confusion_matrix"])
    title = f"{meta['model_name']} {meta['model_version']}"
    plot_confusion_matrix(cm, classes, rdir / "confusion_matrix_test.png",
                          f"{title} - test confusion matrix (n={cm.sum()})")
    plot_per_class_bars(results["test"]["per_class"], classes, rdir / "per_class_test.png",
                        f"{title} - per-class metrics (test)")

    pred_df = pd.DataFrame({"filepath": test_df["filepath"].values, "true_idx": test_y, "pred_idx": test_pred})
    for i, c in enumerate(classes):
        pred_df[f"p_{c}"] = test_probs[:, i].round(6)
    pred_df.to_csv(mdir / "test_predictions.csv", index=False)

    wrong = np.where(test_pred != test_y)[0]
    pd.DataFrame({
        "filepath": test_df["filepath"].iloc[wrong].values,
        "true": [classes[i] for i in test_y[wrong]],
        "predicted": [classes[i] for i in test_pred[wrong]],
        "confidence": test_probs[wrong].max(1).round(4),
    }).to_csv(rdir / "misclassified_test.csv", index=False)

    # robustness to lighting changes
    rob = robustness(model, make_dataset(test_df, bs, training=False, seed=seed), classes)
    rob_df = pd.DataFrame(rob)
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
    for ax, kind, xl in [(axes[0], "brightness_shift", "added gray levels"), (axes[1], "contrast_scale", "contrast factor")]:
        d = rob_df[rob_df["perturbation"] == kind]
        ax.plot(d["value"], d["accuracy"], marker="o", color="#2a6f97")
        ax.set_xlabel(xl); ax.set_ylabel("test accuracy"); ax.set_ylim(0, 1.02)
        ax.set_title(kind.replace("_", " "))
    fig.suptitle(f"{title} - accuracy under synthetic lighting changes (test split)")
    plt.tight_layout(); plt.savefig(rdir / "robustness.png"); plt.close(fig)

    lat = benchmark(model, tuple(meta["input_shape"]))

    evaluation = {
        "model_name": meta["model_name"], "model_version": meta["model_version"],
        "evaluated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "classes": classes, "total_params": meta["total_params"],
        "model_file_mb": round((mdir / "model.keras").stat().st_size / 1e6, 2),
        "validation": results["val"], "test": results["test"],
        "robustness_test": rob,
        "latency_cpu": lat,
        "latency_hardware": {"processor": platform.processor(), "platform": platform.platform(),
                             "tensorflow": tf.__version__},
        "training": {"total_training_seconds": meta["total_training_seconds"], "stages": meta["stages"]},
        "disclaimer": ("Measured on the NEU-CLS academic benchmark (held-out test split, n=270). "
                       "Not an estimate of performance on a production line."),
    }
    write_json(evaluation, mdir / "evaluation.json")

    t = results["test"]
    print(f"{title}  TEST  acc={t['accuracy']:.4f} (95% CI {t['accuracy_ci95_wilson'][0]:.3f}-"
          f"{t['accuracy_ci95_wilson'][1]:.3f})  macroF1={t['macro_f1']:.4f}  errors={len(wrong)}/{t['n']}")
    print(f"{title}  VAL   acc={results['val']['accuracy']:.4f}  macroF1={results['val']['macro_f1']:.4f}")
    for c in classes:
        pc = t["per_class"][c]
        print(f"   {c:16s} P={pc['precision']:.3f} R={pc['recall']:.3f} F1={pc['f1']:.3f}")
    print("   latency batch1 median %.2f ms, p95 %.2f ms; batch32 %.1f img/s" % (
        lat["batch_1"]["median_ms"], lat["batch_1"]["p95_ms"], lat["batch_32"]["throughput_img_per_s"]))
    print("   robustness:", {f"{r['perturbation'][:5]}{r['value']}": round(r["accuracy"], 3) for r in rob})
    print(f"Saved {rel(mdir / 'evaluation.json')} and figures in {rel(rdir)}/")


if __name__ == "__main__":
    main()
