"""Backend settings (environment variables override defaults)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _env(name: str, default: str) -> str:
    return os.environ.get(f"SURFACECHECK_{name}", default)


@dataclass(frozen=True)
class Settings:
    db_url: str = field(default_factory=lambda: _env("DB_URL", f"sqlite:///{(PROJECT_ROOT / 'backend/data/surfacecheck.db').as_posix()}"))
    storage_dir: Path = field(default_factory=lambda: Path(_env("STORAGE_DIR", str(PROJECT_ROOT / "backend/storage"))))
    model_dirs: tuple = field(default_factory=lambda: tuple(_env("MODEL_DIRS", "models/custom_cnn/v1,models/resnet18/v1").split(",")))
    default_model: str = field(default_factory=lambda: _env("DEFAULT_MODEL", "resnet18:v1"))
    policy_path: Path = field(default_factory=lambda: PROJECT_ROOT / _env("POLICY", "configs/decision_policy.yaml"))
    data_config: Path = PROJECT_ROOT / "configs/data.yaml"
    reports_dir: Path = PROJECT_ROOT / "reports"
    cors_origins: tuple = field(default_factory=lambda: tuple(_env("CORS", "http://localhost:5173,http://127.0.0.1:5173").split(",")))
    max_upload_mb: int = 10
    max_batch_files: int = 200


settings = Settings()
