"""Dataset structure and integrity validation.

Checks (ERROR = pipeline must stop, WARNING = documented but allowed):
  ERROR   expected class folder missing / unexpected class folder present
  ERROR   unreadable or corrupt image
  ERROR   image size != configured size
  ERROR   identical pixels under two different class labels (label conflict)
  WARNING per-class count != expected_per_class
  WARNING non-grayscale image (multi-channel with differing channels)
  WARNING exact duplicates within a class
  WARNING near-duplicates (pHash distance <= threshold)
"""
from __future__ import annotations

import hashlib
import itertools
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import imagehash
import numpy as np
from PIL import Image


@dataclass
class ImageRecord:
    path: Path
    label: str
    width: int
    height: int
    mode: str
    sha256: str
    phash: imagehash.ImageHash
    mean: float
    std: float


@dataclass
class ValidationResult:
    records: list[ImageRecord] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    exact_duplicate_groups: list[list[str]] = field(default_factory=list)
    near_duplicate_pairs: list[dict] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _load(path: Path, label: str) -> ImageRecord:
    with Image.open(path) as im:
        im.load()
        mode, (w, h) = im.mode, im.size
        arr = np.asarray(im)
    if arr.ndim == 3:
        if not all(np.array_equal(arr[..., 0], arr[..., c]) for c in range(1, min(arr.shape[2], 3))):
            mode = f"{mode}(color)"
        arr = arr[..., 0]
    gray = Image.fromarray(arr)
    return ImageRecord(
        path=path, label=label, width=w, height=h, mode=mode,
        sha256=hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest(),
        phash=imagehash.phash(gray), mean=float(arr.mean()), std=float(arr.std()),
    )


def validate_dataset(raw_dir: Path, classes: list[str], image_size: tuple[int, int],
                     expected_per_class: int, extensions: list[str],
                     near_dup_max_distance: int) -> ValidationResult:
    res = ValidationResult()
    if not raw_dir.is_dir():
        res.errors.append(f"Dataset directory not found: {raw_dir}")
        return res

    present = sorted(p.name for p in raw_dir.iterdir() if p.is_dir() and not p.name.startswith(("_", ".")))
    for c in classes:
        if c not in present:
            res.errors.append(f"Missing class folder: {c}")
    for p in present:
        if p not in classes:
            res.errors.append(f"Unexpected class folder: {p}")

    exts = {e.lower() for e in extensions}
    for c in classes:
        folder = raw_dir / c
        if not folder.is_dir():
            continue
        files = sorted(f for f in folder.iterdir() if f.is_file())
        imgs = [f for f in files if f.suffix.lower() in exts]
        for f in set(files) - set(imgs):
            res.warnings.append(f"Ignored non-image file: {f.name} in {c}")
        if len(imgs) != expected_per_class:
            res.warnings.append(f"{c}: {len(imgs)} images (expected {expected_per_class})")
        for f in imgs:
            try:
                r = _load(f, c)
            except Exception as e:  # corrupt / unreadable
                res.errors.append(f"Unreadable image {f}: {e}")
                continue
            if (r.width, r.height) != tuple(image_size):
                res.errors.append(f"Wrong size {r.width}x{r.height}: {f}")
            if "color" in r.mode:
                res.warnings.append(f"Non-grayscale image: {f}")
            res.records.append(r)

    # exact duplicates
    by_hash: dict[str, list[ImageRecord]] = defaultdict(list)
    for r in res.records:
        by_hash[r.sha256].append(r)
    for group in by_hash.values():
        if len(group) > 1:
            labels = {g.label for g in group}
            names = [g.path.as_posix() for g in group]
            res.exact_duplicate_groups.append(names)
            if len(labels) > 1:
                res.errors.append(f"Label conflict - identical pixels in classes {sorted(labels)}: {names}")
            else:
                res.warnings.append(f"Exact duplicate within {group[0].label}: {names}")

    # near duplicates (O(n^2) on 64-bit hashes; fine for ~2k images)
    uniq = [g[0] for g in by_hash.values()]
    bits = np.array([r.phash.hash.flatten() for r in uniq], dtype=bool)
    for i, j in itertools.combinations(range(len(uniq)), 2):
        d = int(np.count_nonzero(bits[i] != bits[j]))
        if d <= near_dup_max_distance:
            a, b = uniq[i], uniq[j]
            res.near_duplicate_pairs.append({
                "a": a.path.as_posix(), "b": b.path.as_posix(),
                "label_a": a.label, "label_b": b.label, "distance": d,
            })
    cross = [p for p in res.near_duplicate_pairs if p["label_a"] != p["label_b"]]
    if res.near_duplicate_pairs:
        res.warnings.append(f"{len(res.near_duplicate_pairs)} near-duplicate pairs "
                            f"(pHash <= {near_dup_max_distance}); {len(cross)} cross-class")
    return res
