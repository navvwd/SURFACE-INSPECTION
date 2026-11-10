"""Integrity tests for the generated split manifests (run after training.make_splits)."""
import pandas as pd
import pytest

from ml.utils.config import load_config, resolve

CFG = load_config("configs/data.yaml")
SPLIT_DIR = resolve(CFG["split"]["out_dir"])
SPLITS = ("train", "val", "test")

pytestmark = pytest.mark.skipif(not (SPLIT_DIR / "train.csv").exists(), reason="run training.make_splits first")


@pytest.fixture(scope="module")
def frames():
    return {s: pd.read_csv(SPLIT_DIR / f"{s}.csv") for s in SPLITS}


@pytest.mark.parametrize("a,b", [("train", "val"), ("train", "test"), ("val", "test")])
@pytest.mark.parametrize("col", ["filepath", "sha256", "group_id"])
def test_no_overlap_between_splits(frames, a, b, col):
    assert not set(frames[a][col]) & set(frames[b][col]), f"{col} shared between {a} and {b}"


def test_every_file_exists(frames):
    for df in frames.values():
        assert all(resolve(p).is_file() for p in df["filepath"])


def test_all_classes_in_every_split(frames):
    for df in frames.values():
        assert set(df["label"]) == set(CFG["dataset"]["classes"])


def test_label_idx_matches_config_order(frames):
    idx = {c: i for i, c in enumerate(CFG["dataset"]["classes"])}
    for df in frames.values():
        assert (df["label"].map(idx) == df["label_idx"]).all()


def test_split_fractions_close_to_config(frames):
    total = sum(len(d) for d in frames.values())
    for s in SPLITS:
        assert abs(len(frames[s]) / total - CFG["split"][s]) < 0.01


def test_stratification(frames):
    """Each class should hold roughly the same share of every split (within 1 image)."""
    for df in frames.values():
        counts = df["label"].value_counts()
        assert counts.max() - counts.min() <= 1
