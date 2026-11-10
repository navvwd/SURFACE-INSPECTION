# Implementation Decision Log

Each entry records *what* was decided, *why*, and what it costs. Newest at the bottom.

---

### D-001 · Python 3.11 in a project-local virtual environment
**Decision:** `.venv` created with Python 3.11.9; versions frozen in `requirements.lock.txt`.
**Why:** 3.11 has the broadest TensorFlow wheel support on Windows; isolating dependencies keeps the
global interpreter (used by other projects) untouched and makes the run reproducible.

### D-002 · CPU-only TensorFlow on native Windows
**Decision:** Train and serve on CPU (Intel i7-10850H, 32 GB RAM).
**Why:** TensorFlow dropped native-Windows GPU support after 2.10. The available GPU (Quadro P620, 4 GB)
would require WSL2 + CUDA and gives little speed-up for a 1,800-image, 200×200 dataset.
**Cost:** longer ResNet18 fine-tuning; latency figures are CPU latencies and are reported as such.

### D-003 · ResNet18 in Keras with weights ported from torchvision
**Decision:** Implement ResNet18 (He et al., 2016, BasicBlock variant) in Keras and load the official
torchvision ImageNet weights via a conversion script, verified by comparing logits on identical inputs.
**Why:** `keras.applications` has no ResNet18. Training ResNet18 from scratch would not be transfer
learning; using PyTorch for one model only would split the code base and the Grad-CAM implementation.

### D-004 · Defect-acceptance policy instead of "pass = no defect"
**Decision:** The decision engine combines (a) a configurable per-class policy (`reject` / `review` /
`accept`) with (b) uncertainty gates (low confidence, small top-1/top-2 margin, high entropy, input
checks). Nothing is rejected on confidence alone.
**Why:** NEU-CLS contains **no defect-free class**; the model can only say *which* defect type an image
most resembles, never that a surface is clean. "Pass candidate" therefore means "defect type is
configured as acceptable and the prediction is reliable", and the UI states this limitation.

### D-005 · Dataset source: Hugging Face mirror `newguyme/neu_cls`
**Decision:** No local copy and no Kaggle credentials were available; the 1,800-image parquet mirror
on Hugging Face was downloaded (SHA-256 of files recorded in `docs/DATASET_CARD.md`).
**Why:** Row count (6 × 300) and image size (200×200) match the published NEU-CLS specification.
**Risk:** third-party mirror with no dataset card. If an official copy is obtained, place it in
`dataset/raw/NEU-CLS/<Class>/` and re-run validation + splitting; the pipeline is source-agnostic.

### D-006 · Images stored as single-channel PNG in a class-folder layout
**Decision:** The importer converts parquet rows into `dataset/raw/NEU-CLS/<Class>/<Code>_NNN.png`
plus `provenance.csv` (source file, row, pixel hash).
**Why:** the mirror stored grayscale images as RGB PNGs. All 1,800 were verified R = G = B before
collapsing to one channel, so the conversion is lossless. Plain files make the pipeline identical for
an official download and let the API and reports reference real image files.

### D-007 · Integer-label → class-name mapping verified visually
**Decision:** `0 Crazing, 1 Inclusion, 2 Patches, 3 Pitted_Surface, 4 Rolled-in_Scale, 5 Scratches`.
**Why:** the mirror carries no label names and no original file names. A contact sheet of 8 images per
label was compared against the NEU-CLS defect descriptions (fine crack network; dark elongated spots;
large dark blotches; small pits; scaly flakes; long bright lines). All six matched, and the mapping is
the alphabetical order these exports normally use.
**Limitation:** this is visual verification, not provenance. Stated as such in the dataset card.

### D-008 · Re-split instead of using the mirror's train/test split
**Decision:** The mirror's 1,440/360 split is ignored. Our own stratified 70/15/15 split (seed 42) is
generated and saved as CSV manifests.
**Why:** we need a validation set for early stopping that is separate from the test set, and we need
control over duplicate handling.

### D-009 · Group-aware splitting for duplicates
**Decision:** Exact duplicates (identical pixels) and same-class near-duplicates (64-bit pHash
Hamming distance ≤ 4) are merged into groups; whole groups are assigned to a single split. Cross-class
exact duplicates are a hard error.
**Why:** an image (or a near-copy) in both train and test inflates test accuracy, which is data leakage.
The mirror contains at least one exact duplicate pair (in Patches).

### D-010 · Normalization statistics from training data only
**Decision:** Mean/std are computed on the train split and stored in `dataset/splits/split_report.json`.
EDA pixel statistics are also computed on train only.
**Why:** prevents test-set information from influencing preprocessing or modelling choices.

### D-011 · Augmentation applied only inside the training pipeline (Phase 3)
**Decision:** Augmentation is implemented as on-the-fly `tf.data`/Keras layers active only on the
training dataset. No augmented images are written to disk, so they cannot leak into val/test.

### D-012 · torch upgraded to 2.15 (CPU) for numpy 2 compatibility
**Decision:** TensorFlow 2.20 pulled numpy 2.4; the originally pinned torch 2.2.2 was built for numpy 1.x
and failed (`RuntimeError: Numpy is not available`). torch/torchvision were upgraded to 2.15.0/0.29.2 CPU.
**Why:** torch is used only to export ImageNet ResNet18 weights; upgrading it is lower-risk than
downgrading numpy underneath TensorFlow.

### D-013 · Brightness/contrast shortcut risk (EDA finding → Phase 3 design input)
**Finding:** mean gray level per class ranges from 96.5 (Scratches) to 177.6 (Pitted_Surface); contrast
from 13.1 (Inclusion) to 54.2 (Patches).
**Decision for Phase 3:** (a) brightness/contrast jitter in train-time augmentation; (b) a trivial
baseline classifier on only per-image mean and std, to quantify how much accuracy the shortcut alone
gives; (c) check Grad-CAM maps for attention on defect structure rather than uniform background.
**Why:** a model relying on exposure would fail under a different camera or lighting, which is exactly
the gap between benchmark and factory performance.

### D-014 · Determinism note for TensorFlow on CPU
TensorFlow 2.20 enables oneDNN optimisations by default, which can introduce tiny floating-point
differences between runs. Phase 3 training sets `TF_ENABLE_ONEDNN_OPTS=0` together with op determinism
so that runs with the same seed are repeatable; the cost (slower CPU training) is measured and reported.

### D-015 · BatchNorm momentum 0.9 for the custom CNN (bug found during training)
**Finding:** the first training run (Keras default BN momentum 0.99) showed 78 % train accuracy but ~20 %
(chance-level) validation accuracy after 5 epochs. Diagnosis on the epoch-1 checkpoint, same 270 val images:
inference-mode BN 28.9 % vs training-mode BN 69.6 %; `bn4` moving variance 1.755 vs actual batch variance 0.080.
With only 40 steps/epoch, 0.99-momentum moving averages need ~12 epochs to forget their initialisation, which
coincides with the early-stopping patience, so the run would have stopped on a misleading signal.
**Decision:** momentum 0.9 (PyTorch-equivalent default). Run aborted and restarted; the aborted log is kept in
`logs/train_custom_cnn_attempt1_bn_momentum_0.99_aborted.log`. The restarted run reproduced the first run's
*training* metrics to 4 decimals (BN momentum only affects inference-mode statistics), confirming determinism.

### D-016 · Preprocessing lives inside the saved models
**Decision:** both models accept raw 200×200×1 gray values (0–255). Rescaling, train-set normalisation (CNN),
resize to 224 + gray→RGB + ImageNet normalisation (ResNet18) are Keras layers inside `model.keras`.
**Why:** the API feeds exactly what training fed; no duplicated preprocessing code that could drift (train/serve skew).

### D-017 · Grad-CAM targets and logits layer
Each model exposes a separate pre-softmax `logits` layer; Grad-CAM differentiates the logit, not the softmax
probability (avoids saturated gradients at high confidence). Target layers: CNN `gradcam_target` (25×25),
ResNet18 `layer4_1_out` (7×7). A randomisation sanity check (Adebayo et al., 2018) is part of the evaluation.

### D-018 · Review workflow and statuses
`MANUAL_REVIEW` → `PENDING_REVIEW`; `REJECT_CANDIDATE` → `PENDING_CONFIRMATION` (a person confirms before material
is scrapped); `PASS_CANDIDATE` → `NOT_REQUIRED`; any recorded review → `REVIEWED`. Reviews are appended to their own
table with outcome `CONFIRMED`/`OVERRIDDEN`; predictions and decisions are immutable.

### D-019 · Production-line simulation uses the held-out test split
Simulated batches sample (seeded) from `dataset/splits/test.csv`, which was never used for training or tuning, so
the dashboard can show agreement with dataset labels. Labels are stored for analytics only and never passed to the
model or decision engine. Upload batches have no labels. The UI, API and PDFs state that this is a sequential software
playback with optional artificial pacing and no hardware integration.

### D-020 · Off-contract inputs are converted but always reviewed
Images that are not 200×200 single-channel 8-bit (resized, colour, other bit depth) or are near-uniform are
converted so the model can run, but each deviation is recorded as an input flag and forces `MANUAL_REVIEW`. This is
a minimal out-of-distribution guard; it cannot detect a different steel grade or an unseen defect type.

### D-021 · Default model for the application: ResNet18
**Evidence (test split, n = 270):** ResNet18 0 errors vs custom CNN 3 errors. The exact McNemar test gives p = 0.25,
so the accuracy difference is **not** statistically significant at this sample size. The deciding factor is
robustness to synthetic lighting changes: at contrast ×0.4, ResNet18 scores 97.8 % and the CNN 59.3 %; at brightness ±80,
ResNet18 scores 89.6–91.5 % and the CNN 82.2–87.0 %.
**Cost:** ~2.6× higher CPU latency (24.3 vs 9.4 ms/image) and 26× more parameters. Both models stay selectable in the UI
and API (`SURFACECHECK_DEFAULT_MODEL`).

### D-022 · Reporting caveats for efficiency numbers
Training times come from a laptop CPU that was shared with other jobs (tests, UI checks, the weight port), and the
models ran different numbers of epochs (the CNN ran all 80, ResNet18 early-stopped), so the times are indicative only.
`model.keras` files include Adam optimiser state (≈3× weights). Latency/throughput are measured separately after warm-up
(`ml/evaluation/latency.py`).

### D-023 · Static artefact route renamed to `/artifacts`
The browser smoke test found that the backend's `/reports` static mount shadowed the dashboard's `/reports` page
through the dev proxy (HTTP 404). Figures are now served under `/artifacts`. The single-process build serves
`index.html` for client routes so deep links work.

### D-024 · Marketing website (UI.MD) alongside the console
**Decision:** `/` is a marketing site built to `UI.MD` (Tailwind CSS 3, Framer Motion 11, Lucide). The seven-module
operations console moved unchanged to `/app/*` and is code-split (the website does not download the charting library).
**Honesty rules:** no stock photos and no invented customers. Imagery comes from real NEU-CLS samples and real Grad-CAM output
of the trained ResNet18 (`scripts/make_brand_assets.py` → `frontend/public/brand/brand.json`, examples explicitly selected
for clear heatmaps). Live numbers come from the API; when the API is unreachable, cards say "Demo preview". Accuracy figures
appear only in the Research block, read from the API, with the benchmark caveat. "Sign In" opens the console. The
prototype has **no authentication**.
**Isolation:** Tailwind preflight is disabled. The site's reset uses zero-specificity `:where(.site)` selectors, and every
console rule is scoped under `.shell`, so neither stylesheet can affect the other.
**Note:** no reference screenshot was found in the project. The layout follows UI.MD's written description of it.

### D-025 · Rebrand to COCO SurfaceCheck (UPDATE.MD)
**Decision:** Product name **COCO SurfaceCheck** (the explicit "NEW PRODUCT NAME" in UPDATE.MD), descriptor "Surface
inspection", maker line "A COCO MEDIA PRODUCT", tagline "Precision in Every Inspection.". UPDATE.MD also mentions
"COCO INSPECT" and "COCO Surface inspection". The name is defined once in `frontend/src/brand.js`, so switching variants is a
one-line change. "AI" is removed from the product name and from brand copy. Deep learning, CNN, computer vision and Grad-CAM
are presented as technical architecture.
**Technical renames (behaviour unchanged):** environment variables `INDUSTRIALSIGHT_*` → `SURFACECHECK_*`, SQLite file
`backend/data/industrialsight.db` → `surfacecheck.db` (moved with its data), logger `surfacecheck`, npm package
`coco-surfacecheck-frontend`. Models, dataset, API routes and features are unchanged.
**Kept:** the project folder name `IndustrialSight-AI/` (renaming would break the virtual environment's absolute paths)
and historical training logs (records of past runs).
**Theme:** the dark theme option was removed; the console is light-only in the electric-blue / white / neon-lime identity.
