# Dataset Card — NEU-CLS (as used in COCO SurfaceCheck)

All numbers below were produced by `training.validate_dataset`, `training.make_splits` and
`training.eda` on 2026-11-11. Raw outputs: `reports/dataset/validation_report.json`,
`dataset/splits/split_report.json`, `reports/eda/eda_summary.json`.

## Origin

| | |
|---|---|
| Dataset | NEU surface defect database, classification version (NEU-CLS), Northeastern University (K. Song, Y. Yan) |
| Copy used | Hugging Face mirror `newguyme/neu_cls` (third-party, no dataset card) |
| Files | `train.parquet` SHA-256 `b564124870f8818172ccd2c20bd0d2e48564204cb8162aac4e86dfdd4137ae71` (56,051,474 B)<br>`test.parquet` SHA-256 `682303727c84fba41db6edac5773e3ed0e9efe1bb268b72d2a4c7af98559548d` (14,128,609 B) |
| Format in mirror | RGB PNG bytes, integer labels 0–5, original file names **not** preserved |
| Label names | Mapped visually (see `docs/DECISIONS.md` D-007): 0 Crazing, 1 Inclusion, 2 Patches, 3 Pitted_Surface, 4 Rolled-in_Scale, 5 Scratches |
| Local layout | `dataset/raw/NEU-CLS/<Class>/<Code>_NNN.png` + `provenance.csv` |

## Validation result: PASS

| Check | Result |
|---|---|
| Classes | 6 / 6 present, none unexpected |
| Images per class | 300 each (1,800 total) |
| Size | 200×200 for all 1,800 |
| Channels | all R = G = B in mirror → stored as 1-channel `L` |
| Corrupt / unreadable | 0 |
| Exact duplicates | 1 pair, same class: `Patches/Pa_004.png` = `Patches/Pa_008.png` |
| Near duplicates (pHash ≤ 4) | 0 additional pairs |
| Cross-class label conflicts | 0 |

## Split (seed 42, group-aware, stratified)

| Class | train | val | test |
|---|---:|---:|---:|
| Crazing | 210 | 45 | 45 |
| Inclusion | 210 | 45 | 45 |
| Patches | 210 | 45 | 45 |
| Pitted_Surface | 210 | 45 | 45 |
| Rolled-in_Scale | 210 | 45 | 45 |
| Scratches | 210 | 45 | 45 |
| **Total** | **1,260** | **270** | **270** |

- Shared files / pixel hashes / duplicate groups between any two splits: **0 / 0 / 0**.
- The duplicate pair is kept together (both in train).
- Re-running produces byte-identical manifests.
- Train-only normalization: mean = 0.5044, std = 0.2107 (pixels scaled to [0, 1]).

## EDA findings (train split only)

| Class | mean brightness (gray) | mean contrast (std) |
|---|---:|---:|
| Crazing | 141.4 | 29.2 |
| Inclusion | 106.3 | 13.1 |
| Patches | 132.8 | 54.2 |
| Pitted_Surface | 177.6 | 27.0 |
| Rolled-in_Scale | 117.2 | 16.0 |
| Scratches | 96.5 | 21.9 |

1. **Global brightness/contrast differs strongly between classes.** A model could partly classify by
   overall exposure rather than defect texture (shortcut learning). This would not survive a change of
   camera or lighting in a factory. Mitigation in Phase 3: brightness/contrast augmentation on train,
   a brightness/contrast-only baseline to quantify how much of the task the shortcut explains, and
   Grad-CAM inspection.
2. **Saturation:** Patches and Pitted_Surface have a visible spike of pixels at gray level 255
   (clipped highlights in the original acquisition).
3. **Mean images** show no fixed-position artefact (e.g. borders, watermarks) that a model could exploit.

## Limitations

- Every image contains a defect. There is **no defect-free class**, so no model trained on this data can
  certify a surface as defect-free.
- Small dataset (1,800 images, one steel line, one acquisition setup). Benchmark accuracy will be high
  and must not be read as expected factory performance.
- Third-party mirror: label names are visually verified, not provided by the source.
