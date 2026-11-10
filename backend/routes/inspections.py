from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.database.models import Batch, Inspection, Prediction, Review, utcnow
from backend.database.session import get_db
from backend.services.inspection import run_inspection
from backend.services.registry import registry
from backend.services.serializers import inspection_dict
from backend.settings import settings

router = APIRouter(prefix="/api/inspections", tags=["inspections"])


async def read_upload(f: UploadFile) -> bytes:
    data = await f.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"{f.filename}: larger than {settings.max_upload_mb} MB")
    if not data:
        raise HTTPException(400, f"{f.filename}: empty file")
    return data


def filtered_query(batch_id=None, product_id=None, decision=None, review_status=None,
                   predicted_class=None, model=None, date_from=None, date_to=None, search=None):
    q = select(Inspection).join(Inspection.prediction).join(Inspection.decision)
    if batch_id:
        q = q.where(Inspection.batch_id == batch_id)
    if product_id:
        q = q.where(Inspection.product_id.contains(product_id))
    if decision:
        q = q.where(Inspection.decision.has(decision=decision))
    if review_status:
        q = q.where(Inspection.review_status == review_status)
    if predicted_class:
        q = q.where(Prediction.predicted_class == predicted_class)
    if model and model in registry.model_ids:
        q = q.where(Prediction.model_version_id == registry.model_ids[model])
    if date_from:
        q = q.where(Inspection.created_at >= date_from)
    if date_to:
        q = q.where(Inspection.created_at <= date_to)
    if search:
        s = f"%{search}%"
        q = q.where(Inspection.inspection_id.like(s) | Inspection.product_id.like(s) | Inspection.source_reference.like(s))
    return q


LOAD_OPTS = (selectinload(Inspection.prediction).selectinload(Prediction.model_version),
             selectinload(Inspection.decision), selectinload(Inspection.reviews))


@router.post("", summary="Inspect a single image")
async def inspect_image(file: UploadFile = File(...), product_id: str | None = Form(None),
                        batch_id: str | None = Form(None), model: str | None = Form(None),
                        db: Session = Depends(get_db)):
    data = await read_upload(file)
    batch_id = (batch_id or "").strip() or None
    try:
        model_key = registry.get(model).key
    except KeyError as e:
        raise HTTPException(400, str(e))
    if batch_id and db.get(Batch, batch_id) is None:
        # A batch ID typed by the operator for a single inspection becomes a "manual" batch record.
        db.add(Batch(batch_id=batch_id, source="manual", status="completed", model_key=model_key))
        db.commit()
    try:
        insp = run_inspection(db, data, product_id=(product_id or "").strip() or None, batch_id=batch_id,
                              source_reference=file.filename or "upload", model_key=model_key)
    except ValueError as e:
        raise HTTPException(422, str(e))
    return inspection_dict(insp)


@router.get("", summary="Inspection history with filters and pagination")
def list_inspections(batch_id: str | None = None, product_id: str | None = None, decision: str | None = None,
                     review_status: str | None = None, predicted_class: str | None = None, model: str | None = None,
                     date_from: datetime | None = None, date_to: datetime | None = None, search: str | None = None,
                     limit: int = Query(25, ge=1, le=500), offset: int = Query(0, ge=0),
                     db: Session = Depends(get_db)):
    q = filtered_query(batch_id, product_id, decision, review_status, predicted_class, model, date_from, date_to, search)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.scalars(q.options(*LOAD_OPTS).order_by(Inspection.created_at.desc()).limit(limit).offset(offset)).all()
    return {"total": total, "limit": limit, "offset": offset, "items": [inspection_dict(i, full=False) for i in rows]}


@router.get("/{inspection_id}")
def get_inspection(inspection_id: str, db: Session = Depends(get_db)):
    insp = db.scalar(select(Inspection).options(*LOAD_OPTS).where(Inspection.inspection_id == inspection_id))
    if insp is None:
        raise HTTPException(404, "Inspection not found")
    return inspection_dict(insp)


class ReviewIn(BaseModel):
    reviewer: str = Field(..., min_length=1, max_length=128)
    final_disposition: Literal["PASS", "REJECT", "HOLD"]
    corrected_class: str | None = None
    notes: str | None = Field(None, max_length=2000)


@router.post("/{inspection_id}/review", summary="Record a human review (does not modify the prediction)")
def review_inspection(inspection_id: str, body: ReviewIn, db: Session = Depends(get_db)):
    insp = db.scalar(select(Inspection).options(*LOAD_OPTS).where(Inspection.inspection_id == inspection_id))
    if insp is None:
        raise HTTPException(404, "Inspection not found")
    classes = registry.get(None).classes
    if body.corrected_class and body.corrected_class not in classes:
        raise HTTPException(422, f"corrected_class must be one of {classes}")
    engine_disp = {"PASS_CANDIDATE": "PASS", "REJECT_CANDIDATE": "REJECT"}.get(insp.decision.decision)
    overridden = (body.corrected_class not in (None, insp.prediction.predicted_class)) or \
                 (engine_disp is not None and body.final_disposition != engine_disp)
    insp.reviews.append(Review(reviewer=body.reviewer.strip(), final_disposition=body.final_disposition,
                               corrected_class=body.corrected_class, notes=body.notes,
                               outcome="OVERRIDDEN" if overridden else "CONFIRMED", reviewed_at=utcnow()))
    insp.review_status = "REVIEWED"
    db.commit()
    db.refresh(insp)
    return inspection_dict(insp)
