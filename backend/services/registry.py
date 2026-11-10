"""Loads trained models + decision policy once at start-up and registers model versions in the DB."""
from __future__ import annotations

import logging
import threading

from sqlalchemy import select

from backend.database.models import ModelVersion
from backend.settings import PROJECT_ROOT, settings
from inference.decision_engine import DecisionEngine, DecisionPolicy
from inference.predictor import ModelBundle

log = logging.getLogger("surfacecheck")


class Registry:
    def __init__(self):
        self.bundles: dict[str, ModelBundle] = {}
        self.model_ids: dict[str, int] = {}
        self.policy: DecisionPolicy | None = None
        self.engine: DecisionEngine | None = None
        self.default_key: str | None = None
        self.lock = threading.Lock()   # serialise TF inference/Grad-CAM (single CPU device)

    def load(self, db) -> None:
        for rel_dir in settings.model_dirs:
            d = PROJECT_ROOT / rel_dir.strip()
            if not (d / "model.keras").exists():
                log.warning("Model not found, skipping: %s", d)
                continue
            b = ModelBundle(d)
            self.bundles[b.key] = b
            ev = b.evaluation or {}
            row = db.scalar(select(ModelVersion).where(ModelVersion.name == b.name, ModelVersion.version == b.version))
            if row is None:
                row = ModelVersion(name=b.name, version=b.version, artifact_path=rel_dir.strip())
                db.add(row)
            row.test_accuracy = ev.get("test", {}).get("accuracy")
            row.test_macro_f1 = ev.get("test", {}).get("macro_f1")
            db.commit()
            self.model_ids[b.key] = row.id
            log.info("Loaded model %s", b.key)
        if not self.bundles:
            raise RuntimeError("No trained models found - run the training pipeline first.")
        self.default_key = settings.default_model if settings.default_model in self.bundles else next(iter(self.bundles))
        self.policy = DecisionPolicy.from_yaml(settings.policy_path)
        self.policy.validate(next(iter(self.bundles.values())).classes)
        self.engine = DecisionEngine(self.policy)

    def get(self, key: str | None) -> ModelBundle:
        key = key or self.default_key
        if key not in self.bundles:
            raise KeyError(f"Unknown model '{key}'. Available: {sorted(self.bundles)}")
        return self.bundles[key]


registry = Registry()
