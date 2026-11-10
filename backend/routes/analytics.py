from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.services import analytics
from backend.services.registry import registry

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/overview", summary="Factory overview KPIs")
def overview(db: Session = Depends(get_db)):
    return {**analytics.overview(db, registry.get(None).classes), "default_model": registry.default_key,
            "policy_version": registry.policy.version}


@router.get("/defects", summary="Defect analytics")
def defects(batch_id: str | None = None, date_from: datetime | None = None, date_to: datetime | None = None,
            db: Session = Depends(get_db)):
    return analytics.defect_analytics(db, registry.get(None).classes, batch_id, date_from, date_to)
