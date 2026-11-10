"""Config loading and project-path helpers."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resolve(path: str | Path) -> Path:
    """Resolve a project-relative path to an absolute path."""
    p = Path(path)
    return p if p.is_absolute() else PROJECT_ROOT / p


def rel(path: str | Path) -> str:
    """Return a POSIX path relative to the project root (stable across OSes, used in manifests)."""
    return Path(path).resolve().relative_to(PROJECT_ROOT).as_posix()


def load_config(path: str | Path) -> dict[str, Any]:
    with open(resolve(path), encoding="utf-8") as f:
        return yaml.safe_load(f)


def write_json(obj: Any, path: str | Path) -> Path:
    out = resolve(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str)
    return out
