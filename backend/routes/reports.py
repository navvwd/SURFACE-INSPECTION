from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.models import Batch, Inspection
from backend.database.session import get_db
from backend.routes.inspections import LOAD_OPTS, filtered_query
from backend.services import reports
from backend.services.batches import batch_summary
from backend.services.serializers import inspection_dict

router = APIRouter(prefix="/api/reports", tags=["reports"])


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


@router.get("/inspections.csv", summary="Export (filtered) inspection history as CSV")
def export_csv(batch_id: str | None = None, product_id: str | None = None, decision: str | None = None,
               review_status: str | None = None, predicted_class: str | None = None, model: str | None = None,
               date_from: datetime | None = None, date_to: datetime | None = None, db: Session = Depends(get_db)):
    q = filtered_query(batch_id, product_id, decision, review_status, predicted_class, model, date_from, date_to)
    rows = [inspection_dict(i) for i in db.scalars(q.options(*LOAD_OPTS).order_by(Inspection.created_at)).all()]
    return Response(reports.inspections_csv(rows), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="inspections_{_stamp()}.csv"'})


@router.get("/inspections/{inspection_id}.pdf", summary="Single inspection PDF report")
def inspection_pdf(inspection_id: str, db: Session = Depends(get_db)):
    insp = db.scalar(select(Inspection).options(*LOAD_OPTS).where(Inspection.inspection_id == inspection_id))
    if insp is None:
        raise HTTPException(404, "Inspection not found")
    return Response(reports.inspection_pdf(inspection_dict(insp)), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="inspection_{inspection_id[:8]}.pdf"'})


@router.get("/batches/{batch_id}.pdf", summary="Batch PDF report")
def batch_pdf(batch_id: str, db: Session = Depends(get_db)):
    if db.get(Batch, batch_id) is None:
        raise HTTPException(404, "Batch not found")
    rows = [inspection_dict(i, full=False) for i in db.scalars(
        select(Inspection).options(*LOAD_OPTS).where(Inspection.batch_id == batch_id).order_by(Inspection.sequence_no)).all()]
    return Response(reports.batch_pdf(batch_summary(db, batch_id), rows), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="batch_{batch_id}.pdf"'})
