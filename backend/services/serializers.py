"""ORM -> JSON-ready dicts (single place that defines the API's inspection shape)."""
from __future__ import annotations

from datetime import datetime

from backend.database.models import Batch, Inspection, Review
from inference.gradcam import CAVEAT


def iso(dt: datetime | None) -> str | None:
    return dt.isoformat(timespec="seconds") + "Z" if dt else None


def storage_url(rel: str | None) -> str | None:
    return f"/storage/{rel}" if rel else None


def review_dict(r: Review) -> dict:
    return {"reviewer": r.reviewer, "outcome": r.outcome, "final_disposition": r.final_disposition,
            "corrected_class": r.corrected_class, "notes": r.notes, "reviewed_at": iso(r.reviewed_at)}


def inspection_dict(i: Inspection, full: bool = True) -> dict:
    p, d = i.prediction, i.decision
    out = {
        "inspection_id": i.inspection_id, "product_id": i.product_id, "batch_id": i.batch_id,
        "sequence_no": i.sequence_no, "timestamp": iso(i.created_at),
        "image_reference": i.source_reference, "image_url": storage_url(i.image_path),
        "predicted_class": p.predicted_class, "confidence": round(p.confidence, 6),
        "model_version": f"{p.model_version.name}:{p.model_version.version}",
        "decision": d.decision, "rule_fired": d.rule_fired, "review_status": i.review_status,
        "processing_ms": i.processing_ms, "model_latency_ms": p.latency_ms,
        "ground_truth": i.ground_truth,
    }
    if full:
        out.update({
            "original_url": storage_url(i.original_path), "image_sha256": i.image_sha256,
            "gradcam_url": storage_url(p.gradcam_path), "gradcam_layer": p.gradcam_layer,
            "gradcam_stats": p.gradcam_stats, "gradcam_caveat": CAVEAT,
            "probabilities": p.probabilities, "margin": round(p.margin, 6),
            "normalized_entropy": round(p.normalized_entropy, 6), "input_flags": p.input_flags,
            "decision_reasons": d.reasons, "policy_version": d.policy_version, "decided_at": iso(d.decided_at),
            "reviews": [review_dict(r) for r in i.reviews],
        })
    return out


def batch_dict(b: Batch) -> dict:
    return {"batch_id": b.batch_id, "product_line": b.product_line, "source": b.source, "status": b.status,
            "model_key": b.model_key, "pacing_ms": b.pacing_ms, "notes": b.notes,
            "created_at": iso(b.created_at), "started_at": iso(b.started_at), "finished_at": iso(b.finished_at),
            "n_items": len(b.items), "n_done": sum(it.status == "done" for it in b.items),
            "n_failed": sum(it.status == "failed" for it in b.items)}
