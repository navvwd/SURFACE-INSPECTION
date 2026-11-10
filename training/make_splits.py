"""Step 3 - create leakage-safe stratified train/val/test manifests.

Usage:
    python -m training.make_splits [--config configs/data.yaml]

Outputs (dataset/splits/):
    train.csv, val.csv, test.csv   columns: filepath,label,label_idx,group_id,sha256
    split_report.json              counts, leakage check, train-only normalization stats

Normalization statistics are computed from TRAIN images only, so no information from the
validation or test sets reaches the models.
"""
import argparse
import sys

import numpy as np
import pandas as pd
from PIL import Image

from ml.data.splitting import assign_groups, leakage_report, stratified_group_split
from ml.utils.config import load_config, rel, resolve, write_json
from ml.utils.seed import set_global_seed
from training.validate_dataset import run as run_validation


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/data.yaml")
    args = ap.parse_args()
    cfg = load_config(args.config)
    sp, classes = cfg["split"], cfg["dataset"]["classes"]
    set_global_seed(sp["seed"], deterministic_tf=False)

    res = run_validation(cfg)
    if not res.ok:
        print("Dataset validation failed; fix errors first:\n  " + "\n  ".join(res.errors))
        sys.exit(1)

    df = pd.DataFrame({
        "filepath": [r.path.as_posix() for r in res.records],
        "label": [r.label for r in res.records],
        "sha256": [r.sha256 for r in res.records],
    })
    df["label_idx"] = df["label"].map({c: i for i, c in enumerate(classes)})
    df["group_id"] = assign_groups(df, res.near_duplicate_pairs)
    df = stratified_group_split(df, sp["train"], sp["val"], sp["test"], seed=sp["seed"])
    df["filepath"] = df["filepath"].map(rel)

    leaks = leakage_report(df)
    leak_total = sum(v for d in leaks.values() for v in d.values())

    # train-only normalization statistics (pixel values scaled to [0, 1])
    train_px = np.concatenate([
        np.asarray(Image.open(resolve(p)).convert("L"), dtype=np.float64).ravel() / 255.0
        for p in df.loc[df["split"] == "train", "filepath"]
    ])

    out_dir = resolve(sp["out_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    cols = ["filepath", "label", "label_idx", "group_id", "sha256"]
    for s in ("train", "val", "test"):
        part = df[df["split"] == s].sort_values(["label_idx", "filepath"])
        part[cols].to_csv(out_dir / f"{s}.csv", index=False)

    counts = df.pivot_table(index="label", columns="split", values="filepath", aggfunc="count")
    report = {
        "seed": sp["seed"],
        "fractions": {k: sp[k] for k in ("train", "val", "test")},
        "total": len(df),
        "per_split": df["split"].value_counts().reindex(["train", "val", "test"]).to_dict(),
        "per_class_per_split": counts.reindex(classes)[["train", "val", "test"]].to_dict(orient="index"),
        "duplicate_groups_merged": int((df.groupby("group_id").size() > 1).sum()),
        "leakage_check": leaks,
        "leakage_free": leak_total == 0,
        "normalization_train_only": {"mean": float(train_px.mean()), "std": float(train_px.std())},
    }
    write_json(report, out_dir / "split_report.json")

    print(counts.reindex(classes)[["train", "val", "test"]].to_string())
    print(f"\nTotal: {report['per_split']}   multi-image duplicate groups: {report['duplicate_groups_merged']}")
    print(f"Leakage-free: {report['leakage_free']}  {leaks}")
    print(f"Train-only normalization: mean={report['normalization_train_only']['mean']:.4f} "
          f"std={report['normalization_train_only']['std']:.4f}")
    print(f"Manifests written to {rel(out_dir)}/")
    sys.exit(0 if report["leakage_free"] else 1)


if __name__ == "__main__":
    main()
