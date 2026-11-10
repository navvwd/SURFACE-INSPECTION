"""Compare evaluated models on the same held-out test split.

Usage:
    python -m training.compare_models --models models/custom_cnn/v1 models/resnet18/v1

Includes an exact McNemar test on the paired per-image test predictions: with n=270 test images and
high accuracies, small accuracy differences are often not statistically significant.

Outputs: reports/comparison/model_comparison.{json,md}, model_comparison.png
"""
from __future__ import annotations

import argparse
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import binomtest

from ml.utils.config import rel, resolve, write_json


def load(mdir):
    d = resolve(mdir)
    ev = json.loads((d / "evaluation.json").read_text())
    preds = pd.read_csv(d / "test_predictions.csv")
    dec = d / "decision_analysis.json"
    ev["_decision"] = json.loads(dec.read_text()) if dec.exists() else None
    return ev, preds


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", required=True)
    args = ap.parse_args()
    runs = [load(m) for m in args.models]
    classes = runs[0][0]["classes"]
    out = resolve("reports/comparison"); out.mkdir(parents=True, exist_ok=True)

    rows = []
    for ev, _ in runs:
        t, v = ev["test"], ev["validation"]
        rows.append({
            "model": f"{ev['model_name']}:{ev['model_version']}",
            "params": ev["total_params"], "file_mb": ev["model_file_mb"],
            "train_minutes": round(ev["training"]["total_training_seconds"] / 60, 1),
            "val_accuracy": v["accuracy"], "test_accuracy": t["accuracy"],
            "test_acc_ci95": t["accuracy_ci95_wilson"], "test_macro_f1": t["macro_f1"],
            "test_macro_f1_ci95": t["macro_f1_ci95_bootstrap"], "test_errors": t["n"] - t["correct"],
            "latency_b1_median_ms": ev["latency_cpu"]["batch_1"]["median_ms"],
            "latency_b1_p95_ms": ev["latency_cpu"]["batch_1"]["p95_ms"],
            "throughput_b32_img_s": ev["latency_cpu"]["batch_32"]["throughput_img_per_s"],
            "per_class_f1": {c: t["per_class"][c]["f1"] for c in classes},
            "robustness": {f"{r['perturbation']}={r['value']}": r["accuracy"] for r in ev["robustness_test"]},
            "decision_test": ev["_decision"]["test"] if ev["_decision"] else None,
        })

    mcnemar = None
    if len(runs) == 2:
        a, b = runs[0][1], runs[1][1]
        assert (a["filepath"].values == b["filepath"].values).all(), "test predictions not aligned"
        ca, cb = a["pred_idx"] == a["true_idx"], b["pred_idx"] == b["true_idx"]
        n01, n10 = int((ca & ~cb).sum()), int((~ca & cb).sum())
        p = binomtest(n01, n01 + n10, 0.5).pvalue if n01 + n10 > 0 else 1.0
        mcnemar = {"only_first_correct": n01, "only_second_correct": n10, "both_correct": int((ca & cb).sum()),
                   "both_wrong": int((~ca & ~cb).sum()), "exact_p_value": float(p),
                   "significant_at_0_05": bool(p < 0.05)}

    report = {"test_split_n": runs[0][0]["test"]["n"], "models": rows, "mcnemar_exact": mcnemar,
              "disclaimer": runs[0][0]["disclaimer"]}
    write_json(report, out / "model_comparison.json")

    # markdown table
    md = ["| Metric | " + " | ".join(r["model"] for r in rows) + " |", "|---|" + "---:|" * len(rows)]
    def line(name, f):
        md.append(f"| {name} | " + " | ".join(f(r) for r in rows) + " |")
    line("Parameters", lambda r: f"{r['params']:,}")
    line("Model file incl. optimizer state (MB)", lambda r: f"{r['file_mb']}")
    line("Training time (min, shared CPU, not a controlled benchmark)", lambda r: f"{r['train_minutes']}")
    line("Validation accuracy", lambda r: f"{r['val_accuracy']:.4f}")
    line("Test accuracy [95% CI]", lambda r: f"{r['test_accuracy']:.4f} [{r['test_acc_ci95'][0]:.3f}, {r['test_acc_ci95'][1]:.3f}]")
    line("Test macro-F1 [95% CI]", lambda r: f"{r['test_macro_f1']:.4f} [{r['test_macro_f1_ci95'][0]:.3f}, {r['test_macro_f1_ci95'][1]:.3f}]")
    line("Test errors (of 270)", lambda r: f"{r['test_errors']}")
    for c in classes:
        line(f"F1 {c}", lambda r, c=c: f"{r['per_class_f1'][c]:.3f}")
    line("Latency batch=1 median / p95 (ms)", lambda r: f"{r['latency_b1_median_ms']:.1f} / {r['latency_b1_p95_ms']:.1f}")
    line("Throughput batch=32 (img/s)", lambda r: f"{r['throughput_b32_img_s']:.0f}")
    for key in ("brightness_shift=-60", "brightness_shift=60", "contrast_scale=0.55", "contrast_scale=1.6"):
        line(f"Robustness acc ({key})", lambda r, k=key: f"{r['robustness'].get(k, float('nan')):.3f}")
    if all(r["decision_test"] for r in rows):
        line("Policy automation rate (test)", lambda r: f"{r['decision_test']['automation_rate']:.3f}")
        line("Accuracy of auto-decided (test)", lambda r: f"{r['decision_test']['auto_decided_classification_accuracy']:.4f}")
        line("Escaped reject-class defects", lambda r: f"{r['decision_test']['escaped_reject_class_defects']}")
        line("False rejects", lambda r: f"{r['decision_test']['false_rejects']}")
    if mcnemar:
        md += ["", f"McNemar exact test: only {rows[0]['model']} correct = {mcnemar['only_first_correct']}, "
                   f"only {rows[1]['model']} correct = {mcnemar['only_second_correct']}, "
                   f"p = {mcnemar['exact_p_value']:.4f} "
                   f"({'significant' if mcnemar['significant_at_0_05'] else 'not significant'} at 0.05)."]
    md += ["", f"_{report['disclaimer']}_"]
    (out / "model_comparison.md").write_text("\n".join(md), encoding="utf-8")

    # figure
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.2))
    names = [r["model"] for r in rows]; cols = ["#2a6f97", "#e07a1f", "#6a994e"][:len(rows)]
    acc = [r["test_accuracy"] for r in rows]
    err = np.array([[r["test_accuracy"] - r["test_acc_ci95"][0], r["test_acc_ci95"][1] - r["test_accuracy"]] for r in rows]).T
    axes[0].bar(names, acc, yerr=err, capsize=6, color=cols); axes[0].set_ylim(min(0.8, min(acc) - 0.05), 1.0)
    axes[0].set_title("Test accuracy (95% Wilson CI)")
    x = np.arange(len(classes)); w = 0.8 / len(rows)
    for k, r in enumerate(rows):
        axes[1].bar(x + (k - (len(rows) - 1) / 2) * w, [r["per_class_f1"][c] for c in classes], w, label=r["model"], color=cols[k])
    axes[1].set_xticks(x, classes, rotation=25, ha="right", fontsize=8); axes[1].set_title("Per-class F1 (test)")
    lo = min(r["per_class_f1"][c] for r in rows for c in classes); axes[1].set_ylim(max(0, lo - 0.05), 1.0); axes[1].legend(fontsize=8)
    axes[2].bar(names, [r["latency_b1_median_ms"] for r in rows], color=cols)
    axes[2].set_title("CPU latency, batch=1 (median ms)")
    plt.tight_layout(); plt.savefig(out / "model_comparison.png"); plt.close(fig)

    print("\n".join(md))
    print(f"\nSaved {rel(out)}/model_comparison.(json|md|png)")


if __name__ == "__main__":
    main()
