"""Evaluate the decision engine (policy) on top of a trained model.

Usage:
    python -m training.analyze_decisions --model-dir models/custom_cnn/v1

1. VALIDATION split: sweep the confidence gate and report coverage (share of images decided
   automatically) vs accuracy of the automatically decided images. This is where thresholds may be
   tuned; the test split is not used for tuning.
2. TEST split: apply configs/decision_policy.yaml exactly as the application does and report
   - decision distribution (pass / reject / review)
   - accuracy of predictions that were NOT sent to review
   - decision-level errors measured against the policy applied to the TRUE class:
       escaped_reject : true class is a reject class, engine said PASS_CANDIDATE   (critical)
       false_reject   : true class is not a reject class, engine said REJECT_CANDIDATE
Outputs: <model-dir>/decision_analysis.json, reports/<name>_<version>/coverage_vs_accuracy.png
"""
from __future__ import annotations

import os

os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "1")

import argparse
import json
import math

import matplotlib.pyplot as plt
import numpy as np

from inference.decision_engine import PASS, REJECT, REVIEW, DecisionEngine, DecisionPolicy
from ml.data.pipeline import make_dataset, read_manifest
from ml.utils.config import load_config, rel, resolve, write_json


def probs_for(model, df, bs, seed):
    ys, ps = [], []
    for x, y in make_dataset(df, bs, training=False, seed=seed):
        ps.append(model(x, training=False).numpy()); ys.append(y.numpy())
    return np.concatenate(ys), np.concatenate(ps)


def stats(p):
    s = np.sort(p, axis=1)[:, ::-1]
    pc = np.clip(p, 1e-12, 1)
    ent = -(pc * np.log(pc)).sum(1) / math.log(p.shape[1])
    return p.argmax(1), s[:, 0], s[:, 0] - s[:, 1], ent


def main() -> None:
    import keras

    ap = argparse.ArgumentParser()
    ap.add_argument("--model-dir", required=True)
    ap.add_argument("--policy", default="configs/decision_policy.yaml")
    args = ap.parse_args()
    mdir = resolve(args.model_dir)
    meta = json.loads((mdir / "train_meta.json").read_text())
    classes, seed = meta["classes"], meta["seed"]
    dcfg = load_config(mdir / "data_config.yaml")
    model = keras.models.load_model(mdir / "model.keras")
    policy = DecisionPolicy.from_yaml(resolve(args.policy))
    policy.validate(classes)
    engine = DecisionEngine(policy)
    sd = dcfg["split"]["out_dir"]

    # 1. validation sweep
    yv, pv = probs_for(model, read_manifest(sd, "val"), 64, seed)
    predv, confv, _, _ = stats(pv)
    sweep = []
    for t in np.round(np.arange(0.40, 1.0, 0.02), 2):
        keep = confv >= t
        sweep.append({"threshold": float(t), "coverage": float(keep.mean()),
                      "auto_accuracy": float((predv[keep] == yv[keep]).mean()) if keep.any() else None})

    # 2. test: apply policy
    yt, pt = probs_for(model, read_manifest(sd, "test"), 64, seed)
    predt, conft, margt, entt = stats(pt)
    decisions, rules = [], {}
    for i in range(len(yt)):
        d = engine.decide(classes[predt[i]], float(conft[i]), float(margt[i]), float(entt[i]), [])
        decisions.append(d.decision)
        rules[d.rule_fired] = rules.get(d.rule_fired, 0) + 1
    decisions = np.array(decisions)
    auto = decisions != REVIEW
    true_action = np.array([policy.class_actions[classes[i]] for i in yt])
    escaped = int(((decisions == PASS) & (true_action == "reject")).sum())
    false_rej = int(((decisions == REJECT) & (true_action != "reject")).sum())
    review_correct = int(((decisions == REVIEW) & (predt == yt)).sum())
    review_wrong = int(((decisions == REVIEW) & (predt != yt)).sum())

    result = {
        "model": f"{meta['model_name']}:{meta['model_version']}", "policy_version": policy.version,
        "policy": policy.to_dict(),
        "validation_confidence_sweep": sweep,
        "test": {
            "n": int(len(yt)),
            "decision_counts": {k: int((decisions == k).sum()) for k in (PASS, REJECT, REVIEW)},
            "rule_counts": rules,
            "automation_rate": float(auto.mean()),
            "auto_decided_classification_accuracy": float((predt[auto] == yt[auto]).mean()) if auto.any() else None,
            "misclassifications_total": int((predt != yt).sum()),
            "misclassifications_caught_by_review": review_wrong,
            "correct_predictions_sent_to_review": review_correct,
            "escaped_reject_class_defects": escaped,
            "false_rejects": false_rej,
        },
        "note": "Decision errors are measured against the illustrative policy applied to the true class.",
    }
    write_json(result, mdir / "decision_analysis.json")

    rdir = resolve(f"reports/{meta['model_name']}_{meta['model_version']}")
    s = [r for r in sweep if r["auto_accuracy"] is not None]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot([r["threshold"] for r in s], [r["coverage"] for r in s], label="coverage (auto-decided share)", color="#2a6f97")
    ax.plot([r["threshold"] for r in s], [r["auto_accuracy"] for r in s], label="accuracy of auto-decided", color="#e07a1f")
    ax.axvline(policy.min_confidence, ls="--", color="#888"); ax.text(policy.min_confidence, 0.02, " policy gate", color="#555")
    ax.set_xlabel("confidence threshold"); ax.set_ylim(0, 1.02); ax.legend(loc="lower left")
    ax.set_title(f"{meta['model_name']} - confidence gate trade-off (validation)")
    plt.tight_layout(); plt.savefig(rdir / "coverage_vs_accuracy.png"); plt.close(fig)

    t = result["test"]
    print(json.dumps(t, indent=2))
    print(f"Saved {rel(mdir / 'decision_analysis.json')}")


if __name__ == "__main__":
    main()
