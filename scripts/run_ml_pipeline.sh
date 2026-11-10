#!/usr/bin/env bash
# Full, reproducible ML pipeline (Phases 2-5). Run from the project root:  bash scripts/run_ml_pipeline.sh
# Assumes the parquet mirror is in dataset/raw/_download_hf_neu_cls (see README).
set -euo pipefail
PY=./.venv/Scripts/python.exe; [ -x "$PY" ] || PY=./.venv/bin/python
mkdir -p logs
step() { echo; echo "=== $* ==="; }
if [ "${SKIP_DATA:-0}" != "1" ]; then
  step "data";      $PY -m training.import_dataset --force && $PY -m training.validate_dataset && $PY -m training.make_splits && $PY -m training.eda
  step "baselines"; $PY -m training.baseline_shortcut
  step "port";      $PY -m training.port_resnet18_weights
fi
for M in custom_cnn resnet18; do
  if [[ "${SKIP_TRAIN:-}" != *"$M"* ]]; then
    step "train $M"; $PY -m training.train --config configs/$M.yaml --overwrite 2>&1 | tee logs/train_$M.log
  fi
  step "evaluate $M";  $PY -m training.evaluate --model-dir models/$M/v1 2>&1 | tee logs/eval_$M.log
  step "decisions $M"; $PY -m training.analyze_decisions --model-dir models/$M/v1 2>&1 | tee logs/decisions_$M.log
  step "gradcam $M";   $PY -m training.gradcam_report --model-dir models/$M/v1 2>&1 | tee logs/gradcam_$M.log
done
step "compare"; $PY -m training.compare_models --models models/custom_cnn/v1 models/resnet18/v1 2>&1 | tee logs/compare.log
step "report";  $PY -m training.build_report
