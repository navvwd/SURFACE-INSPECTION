"""Model performance data, read from the artefacts written by the training pipeline (never hardcoded)."""
from __future__ import annotations

import json

import pandas as pd
from fastapi import APIRouter, HTTPException

from backend.services.registry import registry
from backend.settings import settings

router = APIRouter(prefix="/api", tags=["models"])


def _read_json(path):
    return json.loads(path.read_text()) if path.exists() else None


@router.get("/models", summary="Loaded models with headline test metrics")
def list_models():
    out = []
    for key, b in registry.bundles.items():
        ev = b.evaluation or {}
        out.append({"key": key, "name": b.name, "version": b.version, "is_default": key == registry.default_key,
                    "architecture": b.meta["architecture"], "total_params": b.meta["total_params"],
                    "test_accuracy": ev.get("test", {}).get("accuracy"), "test_macro_f1": ev.get("test", {}).get("macro_f1"),
                    "latency_b1_median_ms": ev.get("latency_cpu", {}).get("batch_1", {}).get("median_ms"),
                    "gradcam_layer": b.gradcam_layer, "trained_at": b.meta["trained_at"]})
    return out


@router.get("/models/{name}/{version}", summary="Full evaluation, training history and decision analysis")
def model_detail(name: str, version: str):
    key = f"{name}:{version}"
    if key not in registry.bundles:
        raise HTTPException(404, "Model not loaded")
    b = registry.bundles[key]
    hist = pd.read_csv(b.dir / "history.csv") if (b.dir / "history.csv").exists() else None
    report_prefix = f"/artifacts/{name}_{version}"
    return {
        "key": key, "train_meta": b.meta, "evaluation": b.evaluation,
        "decision_analysis": _read_json(b.dir / "decision_analysis.json"),
        "gradcam_sanity": _read_json(b.dir / "gradcam_sanity.json"),
        "history": hist.to_dict(orient="records") if hist is not None else [],
        "figures": {k: f"{report_prefix}/{f}" for k, f in [
            ("training_curves", "training_curves.png"), ("confusion_matrix", "confusion_matrix_test.png"),
            ("per_class", "per_class_test.png"), ("robustness", "robustness.png"),
            ("coverage", "coverage_vs_accuracy.png"), ("gradcam_examples", "gradcam_examples.png")]
            if (settings.reports_dir / f"{name}_{version}" / f).exists()},
    }


@router.get("/comparison", summary="Model comparison, shortcut baselines and dataset facts")
def comparison():
    return {
        "comparison": _read_json(settings.reports_dir / "comparison/model_comparison.json"),
        "shortcut_baseline": _read_json(settings.reports_dir / "baselines/shortcut_baseline.json"),
        "dataset_validation": _read_json(settings.reports_dir / "dataset/validation_report.json"),
        "figure": "/artifacts/comparison/model_comparison.png"
        if (settings.reports_dir / "comparison/model_comparison.png").exists() else None,
    }


@router.get("/policy", summary="Active decision policy")
def policy():
    return registry.policy.to_dict()
