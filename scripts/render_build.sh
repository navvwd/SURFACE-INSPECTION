#!/usr/bin/env bash
# Build step for Render (or any Linux host). Run from the repository root:  bash scripts/render_build.sh
set -euo pipefail

echo "==> Python dependencies (runtime only)"
pip install --upgrade pip
pip install -r requirements-render.txt

echo "==> Model files (Git LFS -> real files if the host cloned pointers)"
python scripts/fetch_lfs_files.py models/custom_cnn/v1/model.keras models/resnet18/v1/model.keras

echo "==> NEU-CLS images for the simulated production line (optional)"
if [ ! -d dataset/raw/NEU-CLS ]; then
  mkdir -p dataset/raw/_download_hf_neu_cls
  base=https://huggingface.co/datasets/newguyme/neu_cls/resolve/main/data
  if curl -fsSL -o dataset/raw/_download_hf_neu_cls/train.parquet "$base/train-00000-of-00001.parquet" \
     && curl -fsSL -o dataset/raw/_download_hf_neu_cls/test.parquet "$base/test-00000-of-00001.parquet" \
     && python -m training.import_dataset; then
    rm -rf dataset/raw/_download_hf_neu_cls
    echo "dataset ready"
  else
    echo "WARNING: dataset download failed - simulated line batches will be unavailable; uploads still work"
  fi
fi

echo "==> Website: using the pre-built frontend/dist committed to the repo"
test -f frontend/dist/index.html || { echo "ERROR: frontend/dist missing - run 'npm run build' in frontend/ and commit dist"; exit 1; }
echo "==> Build finished"
