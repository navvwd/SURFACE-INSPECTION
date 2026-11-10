"""COCO SurfaceCheck - FastAPI application.

Run (from project root):
    .venv\\Scripts\\python -m uvicorn backend.main:app --port 8000
API docs: http://localhost:8000/docs
"""
from __future__ import annotations

import os

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.database.session import SessionLocal, init_engine
from backend.routes import analytics, batches, inspections, models, reports
from backend.services.registry import registry
from backend.settings import PROJECT_ROOT, settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_engine(settings.db_url)
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    with SessionLocal() as db:
        registry.load(db)
    yield


app = FastAPI(title="COCO SurfaceCheck", version="1.0.0", lifespan=lifespan,
              description="COCO SurfaceCheck - Surface inspection, a COCO MEDIA product. "
                          "Steel-surface defect inspection prototype (NEU-CLS dataset). "
                          "Decisions are candidates for human disposition.")
app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_methods=["*"], allow_headers=["*"])
for r in (inspections, batches, analytics, models, reports):
    app.include_router(r.router)

settings.storage_dir.mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=settings.storage_dir), name="storage")
app.mount("/artifacts", StaticFiles(directory=settings.reports_dir, check_dir=False), name="artifacts")


@app.get("/api/health", tags=["system"])
def health():
    return {"status": "ok", "models": sorted(registry.bundles), "default_model": registry.default_key,
            "policy_version": registry.policy.version if registry.policy else None}


# Serve the built React app (frontend/dist) when present (single-process deployment). Client-side routes such as
# /history or /reports fall back to index.html so deep links and page reloads work.
_dist = PROJECT_ROOT / "frontend" / "dist"
if _dist.exists():
    from fastapi import HTTPException
    from fastapi.responses import FileResponse

    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith(("api/", "storage/", "artifacts/")):
            raise HTTPException(404)
        f = (_dist / full_path).resolve()
        if full_path and f.is_file() and _dist.resolve() in f.parents:
            return FileResponse(f)
        return FileResponse(_dist / "index.html")
