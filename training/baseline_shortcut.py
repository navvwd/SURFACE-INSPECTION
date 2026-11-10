"""Shortcut baselines: how far can we get WITHOUT looking at defect structure?

Two classifiers that see only global intensity statistics (no spatial information):
  A. per-image mean + std of gray level            (2 features)
  B. 32-bin normalised gray-level histogram         (32 features)
Both: standardised features + multinomial logistic regression, fit on TRAIN, model selection on
VAL (regularisation C), reported on TEST.

If these baselines score high, a CNN's accuracy may partly come from exposure/contrast cues that
would not transfer to a different camera or lighting (DECISIONS D-013).

Usage:
    python -m training.baseline_shortcut
"""
from __future__ import annotations

import numpy as np
from PIL import Image
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from ml.data.pipeline import read_manifest
from ml.evaluation.metrics import classification_metrics
from ml.utils.config import load_config, resolve, write_json


def features(df, kind: str) -> np.ndarray:
    out = []
    for p in df["filepath"]:
        a = np.asarray(Image.open(resolve(p)).convert("L"), dtype=np.float64)
        if kind == "mean_std":
            out.append([a.mean(), a.std()])
        else:
            h, _ = np.histogram(a, bins=32, range=(0, 256))
            out.append(h / h.sum())
    return np.array(out)


def main() -> None:
    cfg = load_config("configs/data.yaml")
    classes, sd, seed = cfg["dataset"]["classes"], cfg["split"]["out_dir"], cfg["split"]["seed"]
    dfs = {s: read_manifest(sd, s) for s in ("train", "val", "test")}
    report = {"note": "Global-intensity-only baselines; no spatial information.", "baselines": {}}
    for kind in ("mean_std", "histogram32"):
        X = {s: features(d, kind) for s, d in dfs.items()}
        y = {s: d["label_idx"].to_numpy() for s, d in dfs.items()}
        best = None
        for C in (0.01, 0.1, 1, 10, 100):
            clf = make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=5000, random_state=seed))
            clf.fit(X["train"], y["train"])
            va = (clf.predict(X["val"]) == y["val"]).mean()
            if best is None or va > best[0]:
                best = (va, C, clf)
        va, C, clf = best
        test_m = classification_metrics(y["test"], clf.predict(X["test"]), classes)
        report["baselines"][kind] = {
            "selected_C": C, "val_accuracy": float(va),
            "test_accuracy": test_m["accuracy"], "test_accuracy_ci95_wilson": test_m["accuracy_ci95_wilson"],
            "test_macro_f1": test_m["macro_f1"],
            "test_per_class_recall": {c: v["recall"] for c, v in test_m["per_class"].items()},
        }
        print(f"{kind:12s} C={C:<6} val_acc={va:.4f}  test_acc={test_m['accuracy']:.4f}  "
              f"macroF1={test_m['macro_f1']:.4f}")
    report["chance_accuracy"] = 1 / len(classes)
    write_json(report, "reports/baselines/shortcut_baseline.json")
    print("Saved reports/baselines/shortcut_baseline.json")


if __name__ == "__main__":
    main()
