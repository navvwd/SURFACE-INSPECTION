# COCO SurfaceCheck

**Surface inspection · A COCO MEDIA PRODUCT**

> *Precision in Every Inspection.*

An intelligent industrial surface quality and inspection management platform designed to help manufacturers
identify defects, monitor product quality and improve inspection workflows.

**Technical architecture.** This is an academic deep-learning project on the NEU-CLS steel dataset:
- **Models:** a Custom CNN and ResNet18 (transfer learning), plus computer-vision preprocessing.
- **Explanations:** Grad-CAM heatmaps.
- **Decisions:** a configurable inspection decision engine.
- **Backend:** FastAPI with SQLite.
- **Frontend:** a React website and inspection console, with batch and simulated production-line inspection.

> The project folder is still named `IndustrialSight-AI/` (the earlier working title). Renaming it would break the
> Python virtual environment, which stores absolute paths. Everything inside uses the COCO SurfaceCheck brand.

> **Scope.** Every accuracy figure in this project was measured on the NEU-CLS academic benchmark
> (held-out test split, n = 270). Those figures don't predict performance on a real production line. NEU-CLS
> has **no defect-free class**, so the model identifies *which* defect type an image most resembles; it can't
> certify a clean surface. The production-line mode is a **simulated sequential playback** of stored images,
> with no camera, conveyor or hardware integration.

**Results:** [`reports/FINAL_REPORT.md`](reports/FINAL_REPORT.md) is generated from the pipeline output, with no
hand-typed numbers. Design docs: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) ·
[`docs/DECISIONS.md`](docs/DECISIONS.md) (decision log) · [`docs/DATASET_CARD.md`](docs/DATASET_CARD.md)

## Key findings (from `reports/FINAL_REPORT.md`)

| | Custom CNN | ResNet18 (ImageNet, fine-tuned) |
|---|---:|---:|
| Test accuracy (n=270) [95% CI] | 98.89% [96.8, 99.6] | 100.00% [98.6, 100] |
| Test errors | 3 | 0 |
| CPU latency, batch 1 (median) | 9.4 ms | 24.3 ms |
| Accuracy at contrast ×0.4 (lighting stress test) | 59.3% | 97.8% |
| Parameters | 0.42 M | 11.2 M |

- **The two models aren't significantly different on accuracy.** The McNemar test gives p = 0.25, so with 270 test images ResNet18's 3 extra correct predictions aren't significant. ResNet18 is the default because it's much more **robust to lighting changes**. (DECISIONS D-021)
- **There's a dataset shortcut.** A classifier that sees only each image's mean and std brightness already scores 63.7%, against 16.7% for chance. NEU-CLS classes differ in overall exposure, so lighting robustness matters more than the headline accuracy suggests.
- **The decision engine never let a reject-class defect through and never falsely rejected, on either model.** About 35% of test images go to human review, mostly because two classes (Crazing, Pitted Surface) are set to "review".
- **Grad-CAM depends on what the model learned.** Heatmaps from the trained model and from a randomly initialised one barely correlate: Spearman ρ = 0.07 for the CNN, 0.20 for ResNet18. The heatmaps follow scratches and inclusions closely. For texture-type defects they're spread across the image, and for Patches they often highlight the patch edges. They explain the model's behaviour; they don't outline defects.
- **I found and fixed a BatchNorm momentum bug.** Validation accuracy had collapsed to chance. The diagnosis is in D-015.

---

## Project layout

```
configs/      data.yaml, custom_cnn.yaml, resnet18.yaml, decision_policy.yaml
dataset/      raw/NEU-CLS/<Class>/*.png (generated) · splits/{train,val,test}.csv
ml/           shared library: data (import/validate/split/pipeline), models, evaluation, utils
training/     CLI steps: import, validate, split, eda, baselines, port weights, train, evaluate,
              analyze_decisions, gradcam_report, compare_models, build_report
models/       model registry: <name>/<version>/{model.keras, history.csv, train_meta.json, evaluation.json, ...}
inference/    predictor.py, gradcam.py, decision_engine.py (used by the backend; no training code)
backend/      FastAPI app: routes/, services/, database/ (SQLAlchemy, SQLite)
frontend/     React + Vite + Recharts dashboard (separate npm project)
reports/      generated figures, metrics, comparison and FINAL_REPORT.md
tests/        pytest: split integrity, decision engine, input validation, end-to-end API
```

## 1. Setup (Windows, Python 3.11, Node 18+)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.lock.txt --extra-index-url https://download.pytorch.org/whl/cpu
cd frontend; npm install; cd ..
```

## 2. Data and ML pipeline (reproducible, seed 42)

```powershell
# download the NEU-CLS parquet mirror (or put an official copy in dataset/raw/NEU-CLS/<Class>/ and skip import)
mkdir dataset\raw\_download_hf_neu_cls
curl -L -o dataset/raw/_download_hf_neu_cls/train.parquet https://huggingface.co/datasets/newguyme/neu_cls/resolve/main/data/train-00000-of-00001.parquet
curl -L -o dataset/raw/_download_hf_neu_cls/test.parquet  https://huggingface.co/datasets/newguyme/neu_cls/resolve/main/data/test-00000-of-00001.parquet

# everything: import -> validate -> split -> EDA -> baselines -> weight port -> train/evaluate both models -> compare -> report
bash scripts/run_ml_pipeline.sh
```

Or step by step (`.\.venv\Scripts\python -m training.<step>`):

| Step | Command | Output |
|---|---|---|
| Import mirror | `training.import_dataset` | `dataset/raw/NEU-CLS/` + `provenance.csv` |
| Validate | `training.validate_dataset` | `reports/dataset/validation_report.json` |
| Split | `training.make_splits` | `dataset/splits/*.csv`, `split_report.json` |
| EDA | `training.eda` | `reports/eda/*.png` |
| Shortcut baselines | `training.baseline_shortcut` | `reports/baselines/shortcut_baseline.json` |
| Port ResNet18 weights | `training.port_resnet18_weights` | `models/pretrained/*` + verification |
| Train | `training.train --config configs/custom_cnn.yaml` | `models/custom_cnn/v1/` |
| Evaluate (test) | `training.evaluate --model-dir models/custom_cnn/v1` | `evaluation.json`, figures |
| Decision analysis | `training.analyze_decisions --model-dir ...` | `decision_analysis.json` |
| Grad-CAM report | `training.gradcam_report --model-dir ...` | `gradcam_examples.png`, sanity check |
| Compare | `training.compare_models --models models/custom_cnn/v1 models/resnet18/v1` | `reports/comparison/` |
| Final report | `training.build_report` | `reports/FINAL_REPORT.md` |

Training runs on CPU. TensorFlow ≥ 2.11 has no native-Windows GPU support.

## 3. Run the application

```powershell
# terminal 1 - API (http://127.0.0.1:8000/docs)
.\.venv\Scripts\python -m uvicorn backend.main:app --port 8000

# terminal 2 - dashboard (http://localhost:5173)
cd frontend; npm run dev
```

**Recommended for demos (single process):** `cd frontend; npm run build` once. Then start only the API, and FastAPI
serves the dashboard at **http://127.0.0.1:8000/**. No dev server, proxy or live-reload is involved.
If a page ever shows an error box, the message there says what failed.

Configuration is set with environment variables (`SURFACECHECK_DEFAULT_MODEL`, `_MODEL_DIRS`, `_DB_URL`,
`_STORAGE_DIR`, `_POLICY`). The decision policy lives in `configs/decision_policy.yaml`.

### Website and console

| URL | What it is |
|---|---|
| `/` | Product website built to `UI.MD` (Tailwind, Framer Motion, Lucide). Live stats come from the API; imagery is real NEU-CLS samples and real Grad-CAM output |
| `/app` | Inspection console: the seven modules below |

Regenerate the website imagery after retraining with `python scripts/make_brand_assets.py`. Browser checks:
`python scripts/site_shots.py` (website, 3 widths) and `python scripts/ui_smoke.py --base http://127.0.0.1:8000` (console).

### Console modules

| # | Module | What it shows |
|---|---|---|
| 1 | Factory Overview | KPIs, decisions over time, defect distribution, recent inspections |
| 2 | Image Inspection | Upload → prediction, confidence, probabilities, Grad-CAM (with caveat), decision + rule, review |
| 3 | Batch & Line Simulation | Sequential processing streamed live (SSE): sequence, timing, decisions, batch summary |
| 4 | Defect Analytics | Class × decision, confidence histograms, rules fired, per-batch breakdown, review outcomes |
| 5 | Inspection History | Filter/search/paginate; detail drawer; human review (prediction never modified) |
| 6 | Model Performance | Real evaluation data: curves, per-class metrics, confusion matrix, robustness, comparison, McNemar |
| 7 | Reports | CSV export with filters, PDF per inspection and per batch |

Every inspection stores: inspection ID, product ID, batch ID, image reference, predicted defect, confidence,
model version, timestamp, inspection decision (separate table) and human review status.

## Deploy on Render

Use a **Web Service**, not a Static Site. The website is served by the Python API at the same address.

| Field | Value |
|---|---|
| Root Directory | *(leave empty: the repository root)* |
| Runtime | Python 3 (`.python-version` pins 3.11.9) |
| Build Command | `bash scripts/render_build.sh` |
| Start Command | `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` |
| Health Check Path | `/api/health` |
| Instance | **Standard (2 GB)** for both models. On 512 MB instances, set the env vars below |

Low-memory option (free / starter): `SURFACECHECK_MODEL_DIRS=models/custom_cnn/v1` and `SURFACECHECK_DEFAULT_MODEL=custom_cnn:v1`.

`render.yaml` holds the same settings as a Blueprint (*New → Blueprint*). What the build does:
- installs `requirements-render.txt`, the runtime packages only (no PyTorch)
- turns any Git LFS pointer files into real model files, checking their checksums
- downloads NEU-CLS, which the simulated line needs
- serves the committed `frontend/dist`

Note: Render's filesystem is ephemeral, so the SQLite database and stored images reset on every deploy unless you attach a persistent disk.

## 4. Tests

```powershell
.\.venv\Scripts\python -m pytest
```

The tests cover:
- **Split integrity:** no leakage, stratification, and reproducibility.
- **Decision-engine rules:** including "confidence alone never rejects".
- **Input validation.**
- **End-to-end API tests** against the real trained model, using a temporary database.
