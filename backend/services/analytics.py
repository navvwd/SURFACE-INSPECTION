"""Aggregations for the dashboard (computed from stored inspections - nothing is synthesised)."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.database.models import Batch, Inspection, Prediction, Review, utcnow
from backend.services.serializers import inspection_dict, iso

DECISIONS = ["PASS_CANDIDATE", "REJECT_CANDIDATE", "MANUAL_REVIEW"]


def _load(db, batch_id=None, since: datetime | None = None, until: datetime | None = None):
    q = select(Inspection).options(selectinload(Inspection.prediction).selectinload(Prediction.model_version),
                                   selectinload(Inspection.decision), selectinload(Inspection.reviews))
    if batch_id:
        q = q.where(Inspection.batch_id == batch_id)
    if since:
        q = q.where(Inspection.created_at >= since)
    if until:
        q = q.where(Inspection.created_at <= until)
    return db.scalars(q.order_by(Inspection.created_at)).all()


def overview(db, classes: list[str]) -> dict:
    insps = _load(db)
    now = utcnow()
    last24 = [i for i in insps if i.created_at >= now - timedelta(hours=24)]
    dec = Counter(i.decision.decision for i in insps)
    proc = [i.processing_ms for i in insps]
    # timeline: per hour for the last 24h if all data is recent, else per day
    span_days = (now - insps[0].created_at).days if insps else 0
    fmt = "%Y-%m-%d %H:00" if span_days < 2 else "%Y-%m-%d"
    tl = defaultdict(lambda: Counter())
    for i in insps:
        tl[i.created_at.strftime(fmt)][i.decision.decision] += 1
    return {
        "totals": {"inspections": len(insps), "last_24h": len(last24),
                   "batches": db.query(Batch).count(),
                   "pending_review": sum(i.review_status == "PENDING_REVIEW" for i in insps),
                   "pending_confirmation": sum(i.review_status == "PENDING_CONFIRMATION" for i in insps),
                   "reviewed": sum(i.review_status == "REVIEWED" for i in insps)},
        "decision_counts": {d: dec.get(d, 0) for d in DECISIONS},
        "defect_counts": {c: sum(i.prediction.predicted_class == c for i in insps) for c in classes},
        "avg_processing_ms": float(np.mean(proc)) if proc else None,
        "avg_model_latency_ms": float(np.mean([i.prediction.latency_ms for i in insps])) if insps else None,
        "timeline_granularity": "hour" if span_days < 2 else "day",
        "timeline": [{"bucket": k, **{d: v.get(d, 0) for d in DECISIONS}} for k, v in sorted(tl.items())],
        "recent": [inspection_dict(i, full=False) for i in reversed(insps[-10:])],
    }


def defect_analytics(db, classes: list[str], batch_id=None, since=None, until=None) -> dict:
    insps = _load(db, batch_id, since, until)
    by_class_decision = {c: {d: 0 for d in DECISIONS} for c in classes}
    conf_bins = np.linspace(0, 1, 11)
    conf_hist = {c: [0] * 10 for c in classes}
    for i in insps:
        c = i.prediction.predicted_class
        by_class_decision.setdefault(c, {d: 0 for d in DECISIONS})[i.decision.decision] += 1
        k = min(int(np.digitize(i.prediction.confidence, conf_bins)) - 1, 9)
        conf_hist.setdefault(c, [0] * 10)[k] += 1
    per_batch = defaultdict(lambda: Counter())
    for i in insps:
        if i.batch_id:
            per_batch[i.batch_id][i.prediction.predicted_class] += 1
            per_batch[i.batch_id]["_total"] += 1
            per_batch[i.batch_id][i.decision.decision] += 1
    rules = Counter(i.decision.rule_fired for i in insps)
    reviews = [r for i in insps for r in i.reviews]
    labelled = [i for i in insps if i.ground_truth]
    flags = Counter(f.split("_from_")[0] for i in insps for f in (i.prediction.input_flags or []))
    return {
        "n": len(insps),
        "class_decision_matrix": by_class_decision,
        "confidence_histogram": {"bins": [f"{conf_bins[k]:.1f}-{conf_bins[k+1]:.1f}" for k in range(10)], "counts": conf_hist},
        "mean_confidence_by_class": {c: float(np.mean([i.prediction.confidence for i in insps if i.prediction.predicted_class == c]))
                                     for c in classes if any(i.prediction.predicted_class == c for i in insps)},
        "rule_counts": dict(rules),
        "input_flag_counts": dict(flags),
        "per_batch": [{"batch_id": k, "total": v["_total"], **{c: v.get(c, 0) for c in classes},
                       **{d: v.get(d, 0) for d in DECISIONS}} for k, v in per_batch.items()],
        "review_outcomes": dict(Counter(r.outcome for r in reviews)),
        "review_dispositions": dict(Counter(r.final_disposition for r in reviews)),
        "simulation_ground_truth": {
            "n": len(labelled),
            "accuracy": (sum(i.prediction.predicted_class == i.ground_truth for i in labelled) / len(labelled)) if labelled else None,
            "note": "Agreement with NEU-CLS labels for simulation batches only.",
        },
    }
