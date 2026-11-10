"""Convert the Hugging Face parquet mirror of NEU-CLS into the canonical class-folder layout.

Output: <raw_dir>/<ClassName>/<Code>_<NNN>.png  (single-channel grayscale, lossless)
        <raw_dir>/provenance.csv                (file -> source parquet + row index + pixel hash)

Why: every downstream step (validation, splitting, the inference API) works on plain image files,
so the pipeline is identical whether the data came from this mirror or from an official download.
The mirror stores grayscale images as RGB PNGs; we verify R == G == B before collapsing to one
channel, so no information is lost or invented.
"""
from __future__ import annotations

import csv
import hashlib
import io
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
from PIL import Image


def pixel_sha256(arr: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(arr).tobytes()).hexdigest()


def import_hf_parquet(cfg: dict, project_root: Path, force: bool = False) -> dict:
    ds, src = cfg["dataset"], cfg["source"]
    raw_dir = project_root / ds["raw_dir"]
    dl_dir = project_root / src["download_dir"]
    label_map = {int(k): v for k, v in src["label_map"].items()}
    codes = ds["class_codes"]

    if raw_dir.exists() and any(raw_dir.iterdir()) and not force:
        raise FileExistsError(f"{raw_dir} is not empty; pass --force to rebuild it.")

    for cls in ds["classes"]:
        (raw_dir / cls).mkdir(parents=True, exist_ok=True)

    counters = {c: 0 for c in ds["classes"]}
    provenance = []
    for split_name, fname in src["files"].items():
        table = pq.read_table(dl_dir / fname)
        for row_idx, row in enumerate(table.to_pylist()):
            cls = label_map[int(row["label"])]
            arr = np.asarray(Image.open(io.BytesIO(row["image"]["bytes"])))
            if arr.ndim == 3:
                if not (np.array_equal(arr[..., 0], arr[..., 1]) and np.array_equal(arr[..., 1], arr[..., 2])):
                    raise ValueError(f"{fname} row {row_idx}: channels differ; image is not grayscale")
                arr = arr[..., 0]
            counters[cls] += 1
            out = raw_dir / cls / f"{codes[cls]}_{counters[cls]:03d}.png"
            Image.fromarray(arr.astype(np.uint8), mode="L").save(out)
            provenance.append({
                "file": out.relative_to(project_root).as_posix(),
                "class": cls,
                "source_repo": src["repo"],
                "source_file": fname,
                "source_split": split_name,
                "source_row": row_idx,
                "source_label": int(row["label"]),
                "pixel_sha256": pixel_sha256(arr),
            })

    with open(raw_dir / "provenance.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(provenance[0].keys()))
        w.writeheader()
        w.writerows(provenance)
    return {"written": len(provenance), "per_class": counters, "raw_dir": str(raw_dir)}
