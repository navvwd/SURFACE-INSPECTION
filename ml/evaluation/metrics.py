"""Classification metrics with uncertainty estimates."""
from __future__ import annotations

import math

import numpy as np
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a binomial proportion (better than normal approx near 1.0)."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z ** 2 / n
    centre = (p + z ** 2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def bootstrap_ci(y_true, y_pred, fn, n_boot: int = 2000, seed: int = 42) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    n = len(y_true)
    stats = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        stats.append(fn(y_true[idx], y_pred[idx]))
    return (float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5)))


def classification_metrics(y_true: np.ndarray, y_pred: np.ndarray, classes: list[str]) -> dict:
    labels = list(range(len(classes)))
    p, r, f, s = precision_recall_fscore_support(y_true, y_pred, labels=labels, zero_division=0)
    acc = accuracy_score(y_true, y_pred)
    k = int((y_true == y_pred).sum())
    macro_f1 = f1_score(y_true, y_pred, average="macro", labels=labels, zero_division=0)
    return {
        "n": int(len(y_true)),
        "correct": k,
        "accuracy": float(acc),
        "accuracy_ci95_wilson": wilson_interval(k, len(y_true)),
        "macro_precision": float(p.mean()),
        "macro_recall": float(r.mean()),
        "macro_f1": float(macro_f1),
        "macro_f1_ci95_bootstrap": bootstrap_ci(
            y_true, y_pred, lambda a, b: f1_score(a, b, average="macro", labels=labels, zero_division=0)),
        "per_class": {c: {"precision": float(p[i]), "recall": float(r[i]), "f1": float(f[i]), "support": int(s[i])}
                      for i, c in enumerate(classes)},
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
    }
