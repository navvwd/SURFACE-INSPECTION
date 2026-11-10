from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.database.models import Batch
from backend.database.session import SessionLocal, get_db
from backend.routes.inspections import read_upload
from backend.services.batches import (SIMULATION_NOTICE, batch_summary, create_simulation_batch,
                                      create_upload_batch, run_batch)
from backend.services.registry import registry
from backend.services.serializers import batch_dict
from backend.settings import settings

router = APIRouter(prefix="/api/batches", tags=["batches"])


def _model_key(model: str | None) -> str:
    try:
        return registry.get(model).key
    except KeyError as e:
        raise HTTPException(400, str(e))


@router.post("", summary="Create an upload batch (queued; run it via /run)")
async def create_batch(files: list[UploadFile] = File(...), product_line: str | None = Form(None),
                       model: str | None = Form(None), pacing_ms: int = Form(0),
                       product_prefix: str | None = Form(None), db: Session = Depends(get_db)):
    if len(files) > settings.max_batch_files:
        raise HTTPException(413, f"At most {settings.max_batch_files} files per batch")
    payload = [(f.filename or f"file{i}", await read_upload(f)) for i, f in enumerate(files)]
    b = create_upload_batch(db, payload, product_line, _model_key(model), max(0, min(pacing_ms, 5000)), product_prefix)
    return batch_dict(b)


class SimulationIn(BaseModel):
    n_images: int = Field(20, ge=1, le=270)
    seed: int = 7
    model: str | None = None
    pacing_ms: int = Field(400, ge=0, le=5000)
    product_line: str | None = "Hot-rolled strip line (simulated)"


@router.post("/simulate", summary="Create a simulated production-line batch from the held-out test split")
def create_simulation(body: SimulationIn, db: Session = Depends(get_db)):
    b = create_simulation_batch(db, body.n_images, body.seed, _model_key(body.model), body.pacing_ms, body.product_line)
    return {**batch_dict(b), "notice": SIMULATION_NOTICE}


@router.get("/{batch_id}/run", summary="Process the batch sequentially, streaming Server-Sent Events")
def run(batch_id: str):
    db = SessionLocal()
    b = db.get(Batch, batch_id)
    if b is None:
        db.close()
        raise HTTPException(404, "Batch not found")
    if b.status == "running":
        db.close()
        raise HTTPException(409, "Batch is already running")

    def stream():
        try:
            yield f"event: start\ndata: {json.dumps({'batch_id': batch_id, 'notice': SIMULATION_NOTICE})}\n\n"
            for kind, payload in run_batch(db, batch_id):
                yield f"event: {kind}\ndata: {json.dumps(payload)}\n\n"
        except Exception as e:  # surface failure to the client instead of a silent disconnect
            yield f"event: failure\ndata: {json.dumps({'error': str(e)})}\n\n"
        finally:
            db.close()

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("", summary="List batches")
def list_batches(db: Session = Depends(get_db)):
    rows = db.scalars(select(Batch).options(selectinload(Batch.items)).order_by(Batch.created_at.desc())).all()
    return [batch_dict(b) for b in rows]


@router.get("/{batch_id}", summary="Batch details and batch-level summary")
def get_batch(batch_id: str, db: Session = Depends(get_db)):
    b = db.get(Batch, batch_id)
    if b is None:
        raise HTTPException(404, "Batch not found")
    return {**batch_dict(b), "summary": batch_summary(db, batch_id)}
