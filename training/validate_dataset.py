"""Step 2 - validate dataset structure and integrity.

Usage:
    python -m training.validate_dataset [--config configs/data.yaml]

Writes reports/dataset/validation_report.json and near_duplicates.csv.
Exit code 1 if any ERROR-level problem is found.
"""
import argparse
import sys
from collections import Counter

import pandas as pd

from ml.data.validation import validate_dataset
from ml.utils.config import load_config, rel, resolve, write_json


def run(cfg: dict):
    ds, sp = cfg["dataset"], cfg["split"]
    return validate_dataset(
        raw_dir=resolve(ds["raw_dir"]), classes=ds["classes"], image_size=tuple(ds["image_size"]),
        expected_per_class=ds["expected_per_class"], extensions=ds["allowed_extensions"],
        near_dup_max_distance=sp["near_duplicate_max_distance"],
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/data.yaml")
    cfg = load_config(ap.parse_args().config)
    res = run(cfg)

    out_dir = resolve(cfg["reports"]["dataset_dir"])
    counts = Counter(r.label for r in res.records)
    report = {
        "status": "PASS" if res.ok else "FAIL",
        "dataset": cfg["dataset"]["name"],
        "raw_dir": cfg["dataset"]["raw_dir"],
        "source": {k: cfg["source"][k] for k in ("type", "repo", "revision", "label_map_verification")},
        "total_images": len(res.records),
        "per_class": {c: counts.get(c, 0) for c in cfg["dataset"]["classes"]},
        "sizes": dict(Counter(f"{r.width}x{r.height}" for r in res.records)),
        "modes": dict(Counter(r.mode for r in res.records)),
        "exact_duplicate_groups": [[rel(p) for p in g] for g in res.exact_duplicate_groups],
        "near_duplicate_pairs": len(res.near_duplicate_pairs),
        "errors": res.errors,
        "warnings": res.warnings,
    }
    write_json(report, out_dir / "validation_report.json")
    if res.near_duplicate_pairs:
        nd = pd.DataFrame(res.near_duplicate_pairs)
        nd["a"], nd["b"] = nd["a"].map(rel), nd["b"].map(rel)
        nd.sort_values("distance").to_csv(out_dir / "near_duplicates.csv", index=False)

    print(f"Validation: {report['status']}  ({report['total_images']} images)")
    for c, n in report["per_class"].items():
        print(f"  {c:16s} {n}")
    print(f"  sizes={report['sizes']}  modes={report['modes']}")
    for w in res.warnings:
        print("  WARNING:", w)
    for e in res.errors:
        print("  ERROR:  ", e)
    print(f"Report: {rel(out_dir / 'validation_report.json')}")
    sys.exit(0 if res.ok else 1)


if __name__ == "__main__":
    main()
