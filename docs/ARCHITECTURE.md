# COCO SurfaceCheck — Architecture

*Surface inspection · A COCO MEDIA PRODUCT · "Precision in Every Inspection."*

Steel-surface defect classification (NEU-CLS, 6 classes) with explainability (Grad-CAM), a
configurable inspection decision engine, a FastAPI + SQLite backend, a React product website (`/`)
and an inspection console (`/app`). Deep learning, CNNs, computer vision and Grad-CAM belong to the technical
architecture, not the product name.

> **Scope statement.** This is an academic prototype. All accuracy figures are measured on the NEU-CLS
> benchmark and do **not** predict performance on a real production line, where lighting, cameras,
> steel grades and unseen defect types differ. The production-line mode is a *simulated sequential
> playback of stored images*; there is no conveyor or camera integration.

## Layers

```
 ┌──────────────────────── Training (offline, CLI) ────────────────────────┐
 │ configs/*.yaml → training/*.py → ml/ (data, models, evaluation, utils)  │
 │                         ↓ writes                                        │
 │      models/<name>/<version>/  (model.keras, config, metrics, history)  │
 │      reports/                  (EDA, curves, confusion matrices)        │
 └─────────────────────────────────────────────────────────────────────────┘
                              ↓ read-only
 ┌──────────────────── inference/ (shared, no training code) ──────────────┐
 │ predictor.py → gradcam.py → decision_engine.py (configs/decision_policy)│
 └─────────────────────────────────────────────────────────────────────────┘
                              ↓ imported by
 ┌──────────── backend/ (FastAPI) ────────────┐      ┌──── frontend/ ────┐
 │ routes → services → database (SQLAlchemy)  │◀────▶│ React+Vite        │
 │ storage/ (uploads, heatmaps)  SQLite file  │ REST │ Recharts          │
 └────────────────────────────────────────────┘ +SSE └───────────────────┘
```

The frontend never imports Python code, and the backend never imports training code. The only
contract between training and the application is the model registry folder plus `configs/data.yaml`
(class order).

## Folder layout

| Path | Purpose |
|---|---|
| `configs/` | All tunable settings: data/split, per-model training, decision policy |
| `dataset/raw/NEU-CLS/<Class>/` | Canonical images (never modified after import) |
| `dataset/splits/` | `train/val/test.csv` manifests + `split_report.json` |
| `ml/` | Importable library: `data/`, `models/`, `evaluation/`, `utils/` |
| `training/` | Thin CLI entry points (`python -m training.<step>`) |
| `models/` | Versioned model artifacts |
| `inference/` | Prediction, Grad-CAM, decision engine |
| `backend/` | FastAPI app, routes, services, DB models, file storage |
| `frontend/` | React dashboard (separate npm project) |
| `reports/` | Generated figures/tables and exported inspection reports |
| `tests/` | pytest suites |
| `docs/` | This file, `DECISIONS.md`, dataset card, model cards |

## Data pipeline (Phase 2)

1. `training.import_dataset` parquet mirror → class folders + provenance
2. `training.validate_dataset` structure, size, mode, corruption, duplicates → report
3. `training.make_splits` group-aware stratified 70/15/15, leakage check, train-only stats
4. `training.eda` figures + summary

## Models (Phases 3–4)

| | Custom CNN | ResNet18 |
|---|---|---|
| Input | 200×200×1 | 224×224×3 (gray replicated), ImageNet normalization |
| Init | random (seeded) | ImageNet weights ported from torchvision |
| Training | single stage | stage 1 head only → stage 2 fine-tune upper blocks |
| Grad-CAM layer | last conv block | `layer4` output |

Both models: same split manifests, same augmentation policy (train only), early stopping on val loss,
one final evaluation on test.

## Database schema (Phase 6)

Predictions and decisions are stored separately, so a policy change or human review never rewrites
what the model actually said.

```
model_versions(id, name, version, artifact_path, metrics_json, created_at)
batches(batch_id, product_line, started_at, finished_at, mode)
inspections(inspection_id UUID, product_id, batch_id → batches, image_path, created_at)
predictions(id, inspection_id → inspections, model_version_id → model_versions,
            predicted_class, confidence, probabilities_json, latency_ms, gradcam_path)
decisions(id, inspection_id → inspections, decision ∈ {PASS_CANDIDATE, REJECT_CANDIDATE, MANUAL_REVIEW},
          rule_fired, policy_version, decided_at)
reviews(id, inspection_id → inspections, reviewer, status, final_verdict, notes, reviewed_at)
```

## Roadmap

| Phase | Deliverable | Status |
|---|---|---|
| 1 | Environment + architecture plan | done |
| 2 | Dataset import, validation, splits, EDA | done |
| 3 | Custom CNN training + evaluation | done |
| 4 | ResNet18 port + fine-tune + comparison | done |
| 5 | Grad-CAM + decision engine (+ unit tests) | done |
| 6 | FastAPI + SQLite | done |
| 7 | React dashboard (7 modules) | done |
| 8 | Batch simulation (SSE), E2E tests, final report | done |
