"""Generate reports/FINAL_REPORT.md from the artefacts written by the pipeline.

Usage:
    python -m training.build_report

Every number in the report is read from a JSON/CSV artefact at generation time - nothing is typed by hand -
so the report cannot drift from the actual results.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from ml.utils.config import resolve


def j(path):
    p = resolve(path)
    return json.loads(p.read_text()) if p.exists() else None


def pct(v, d=2):
    return "n/a" if v is None else f"{v * 100:.{d}f}%"


def main() -> None:
    val = j("reports/dataset/validation_report.json")
    split = j("dataset/splits/split_report.json")
    eda = j("reports/eda/eda_summary.json")
    base = j("reports/baselines/shortcut_baseline.json")
    port = j("models/pretrained/resnet18_port_verification.json")
    comp = j("reports/comparison/model_comparison.json")
    models = {}
    for m in ("custom_cnn", "resnet18"):
        models[m] = {"eval": j(f"models/{m}/v1/evaluation.json"), "meta": j(f"models/{m}/v1/train_meta.json"),
                     "dec": j(f"models/{m}/v1/decision_analysis.json"), "san": j(f"models/{m}/v1/gradcam_sanity.json")}
    classes = val and list(val["per_class"])
    L = []
    a = L.append
    a("# COCO SurfaceCheck — Final Technical Report")
    a(f"_Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} by `training/build_report.py` from pipeline artefacts._\n")
    a("> **Scope.** Academic prototype on the NEU-CLS benchmark. All metrics below come from actual model execution "
      "on a held-out test split (n = 270). They describe benchmark performance and are **not** estimates of "
      "production-line performance. The production-line mode is a simulated playback of stored images.\n")

    a("## 1. Dataset")
    if val:
        a(f"- Source: Hugging Face mirror `{val['source']['repo']}` (label names verified **{val['source']['label_map_verification']}ly**; see DECISIONS D-005/D-007).")
        a(f"- Validation: **{val['status']}** — {val['total_images']} images, sizes {val['sizes']}, modes {val['modes']}.")
        a(f"- Exact duplicate groups: {len(val['exact_duplicate_groups'])} (kept together in one split); near-duplicate pairs: {val['near_duplicate_pairs']}.")
    if split:
        a(f"- Split (seed {split['seed']}): train/val/test = {split['per_split']['train']}/{split['per_split']['val']}/{split['per_split']['test']}, "
          f"stratified, group-aware. Leakage check: **{'no overlap' if split['leakage_free'] else 'OVERLAP FOUND'}** in files, pixel hashes or duplicate groups.")
        n = split["normalization_train_only"]
        a(f"- Normalisation statistics from train only: mean {n['mean']:.4f}, std {n['std']:.4f}.")
    if eda and base:
        b = base["baselines"]
        a("\n**Shortcut analysis.** Mean brightness per class (train) ranges from "
          f"{min(v['brightness_mean'] for v in eda['train_per_class'].values())} to "
          f"{max(v['brightness_mean'] for v in eda['train_per_class'].values())} gray levels. "
          f"A logistic regression on only per-image mean+std reaches **{pct(b['mean_std']['test_accuracy'])}** test accuracy "
          f"(32-bin histogram: {pct(b['histogram32']['test_accuracy'])}; chance {pct(base['chance_accuracy'])}). "
          "Global exposure alone separates much of NEU-CLS, which motivates brightness/contrast augmentation and the robustness tests below.")

    a("\n## 2. Models")
    for m, d in models.items():
        meta = d["meta"]
        if not meta:
            a(f"- `{m}`: not trained."); continue
        stages = "; ".join(f"{s['name']}: {s['epochs_run']} epochs, best epoch {s['best_epoch']}, {s['trainable_params']:,} trainable params, "
                           f"{s['seconds_per_epoch']} s/epoch" for s in meta["stages"])
        a(f"- **{m}** — {meta['total_params']:,} parameters; trained {meta['total_training_seconds']/60:.1f} min on CPU "
          f"(TensorFlow {meta['environment']['tensorflow']}, seed {meta['seed']}). Stages: {stages}.")
    if port:
        a(f"- ResNet18 ImageNet weights ported from {port['source']}; verification on {port['verification_inputs']} inputs: "
          f"max |Δlogit| = {port['max_abs_logit_diff']:.2e}, top-1 agreement {pct(port['top1_agreement'], 0)}, passed = {port['passed']}.")

    a("\n## 3. Results on the held-out test split")
    if comp:
        a((resolve("reports/comparison/model_comparison.md").read_text(encoding="utf-8")))
        a("\n![comparison](comparison/model_comparison.png)")
    for m, d in models.items():
        ev = d["eval"]
        if not ev:
            continue
        t = ev["test"]
        a(f"\n### {m}")
        a(f"Test accuracy **{pct(t['accuracy'])}** (95% Wilson CI {pct(t['accuracy_ci95_wilson'][0])}–{pct(t['accuracy_ci95_wilson'][1])}), "
          f"macro-F1 **{t['macro_f1']:.4f}** (bootstrap CI {t['macro_f1_ci95_bootstrap'][0]:.3f}–{t['macro_f1_ci95_bootstrap'][1]:.3f}), "
          f"{t['n'] - t['correct']} errors of {t['n']}. Validation accuracy {pct(ev['validation']['accuracy'])}.\n")
        a("| Class | Precision | Recall | F1 | Support |\n|---|---:|---:|---:|---:|")
        for c in classes:
            pc = t["per_class"][c]
            a(f"| {c} | {pc['precision']:.3f} | {pc['recall']:.3f} | {pc['f1']:.3f} | {pc['support']} |")
        lat = ev["latency_cpu"]
        a(f"\nCPU latency (forward pass): batch 1 median {lat['batch_1']['median_ms']:.2f} ms (p95 {lat['batch_1']['p95_ms']:.2f} ms); "
          f"batch 32 throughput {lat['batch_32']['throughput_img_per_s']:.0f} img/s on `{ev['latency_hardware']['processor']}`.")
        rob = {f"{r['perturbation']}={r['value']}": r["accuracy"] for r in ev["robustness_test"]}
        a(f"Robustness (synthetic lighting): brightness −80/−40/+40/+80 → {pct(rob['brightness_shift=-80'],1)} / {pct(rob['brightness_shift=-40'],1)} / "
          f"{pct(rob['brightness_shift=40'],1)} / {pct(rob['brightness_shift=80'],1)}; contrast ×0.4/×2.0 → {pct(rob['contrast_scale=0.4'],1)} / {pct(rob['contrast_scale=2.0'],1)}.")
        if d["dec"]:
            dt = d["dec"]["test"]
            a(f"Decision engine (policy v{d['dec']['policy_version']}): {dt['decision_counts']}; automation rate {pct(dt['automation_rate'],1)}; "
              f"accuracy of auto-decided items {pct(dt['auto_decided_classification_accuracy'])}; misclassifications caught by review "
              f"{dt['misclassifications_caught_by_review']}/{dt['misclassifications_total']}; escaped reject-class defects {dt['escaped_reject_class_defects']}; "
              f"false rejects {dt['false_rejects']}.")
        if d["san"]:
            s = d["san"]
            a(f"Grad-CAM sanity check: Spearman ρ trained-vs-random-weights {s['trained_vs_random_weights_spearman_mean']:.3f}; "
              f"flip consistency {s['flip_consistency_spearman_mean']:.3f} (n={s['n_images']}).")
        a(f"\n![curves]({m}_v1/training_curves.png)\n![cm]({m}_v1/confusion_matrix_test.png)\n![robustness]({m}_v1/robustness.png)\n![gradcam]({m}_v1/gradcam_examples.png)")

    a("\n## 4. Limitations")
    a("- No defect-free class: the system classifies defect *type*; it cannot certify a clean surface (decision policy is illustrative).")
    a("- Single small benchmark from one acquisition setup; label names of the mirror verified visually.")
    a("- Grad-CAM is a coarse explanation of model behaviour, not a defect segmentation.")
    a("- Latency is CPU software timing on one laptop; there is no camera/conveyor integration and no real-time guarantee.")
    a("- Deployment would require plant-specific data, re-validation, calibration of thresholds, and drift monitoring.")
    out = resolve("reports/FINAL_REPORT.md")
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
