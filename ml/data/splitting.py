"""Leakage-aware stratified train/val/test split.

Images that are exact or near duplicates of each other (same class) are merged into one
"group" with union-find, and whole groups are assigned to a split. That way a duplicate can
never appear in both train and test. Stratification is done on the group label, so class
balance is preserved.

Cross-class near-duplicates are NOT merged (merging would mix labels inside a group); they are
reported by the validator instead.
"""
from __future__ import annotations

import pandas as pd
from sklearn.model_selection import train_test_split


class _UnionFind:
    def __init__(self, items):
        self.parent = {i: i for i in items}

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)


def assign_groups(df: pd.DataFrame, near_dup_pairs: list[dict]) -> pd.Series:
    """df has columns filepath, label, sha256. Returns a group id per row."""
    uf = _UnionFind(df["filepath"].tolist())
    for _, grp in df.groupby("sha256"):
        files = grp["filepath"].tolist()
        for f in files[1:]:
            uf.union(files[0], f)
    sha_to_file = df.groupby("sha256")["filepath"].first().to_dict()
    file_to_sha = dict(zip(df["filepath"], df["sha256"]))
    for p in near_dup_pairs:
        if p["label_a"] == p["label_b"]:
            uf.union(sha_to_file[file_to_sha[p["a"]]], sha_to_file[file_to_sha[p["b"]]])
    roots = df["filepath"].map(uf.find)
    return roots.map({r: i for i, r in enumerate(sorted(roots.unique()))})


def stratified_group_split(df: pd.DataFrame, train: float, val: float, test: float,
                           seed: int) -> pd.DataFrame:
    """Adds a `split` column. Splits at group level, stratified by label."""
    assert abs(train + val + test - 1.0) < 1e-9, "split fractions must sum to 1"
    groups = df.groupby("group_id")["label"].first().reset_index()
    g_trainval, g_test = train_test_split(groups, test_size=test, stratify=groups["label"],
                                          random_state=seed)
    g_train, g_val = train_test_split(g_trainval, test_size=val / (train + val),
                                      stratify=g_trainval["label"], random_state=seed)
    split_of = {**{g: "train" for g in g_train["group_id"]},
                **{g: "val" for g in g_val["group_id"]},
                **{g: "test" for g in g_test["group_id"]}}
    out = df.copy()
    out["split"] = out["group_id"].map(split_of)
    return out


def leakage_report(df: pd.DataFrame) -> dict:
    """Pairwise overlap of files, pixel hashes and duplicate groups between splits (all must be 0)."""
    sets = {s: d for s, d in df.groupby("split")}
    report = {}
    for a, b in [("train", "val"), ("train", "test"), ("val", "test")]:
        A, B = sets[a], sets[b]
        report[f"{a}-{b}"] = {
            "shared_files": len(set(A["filepath"]) & set(B["filepath"])),
            "shared_pixel_hashes": len(set(A["sha256"]) & set(B["sha256"])),
            "shared_duplicate_groups": len(set(A["group_id"]) & set(B["group_id"])),
        }
    return report
