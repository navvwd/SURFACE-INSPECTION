"""Inspection pipeline: decode -> validate -> predict -> Grad-CAM -> decide -> store -> persist."""
from __future__ import annotations

import hashlib
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import cv2

from backend.database.models import Decision, Inspection, Prediction
from backend.services.registry import registry
from backend.settings import settings
from inference.decision_engine import PASS, REJECT, REVIEW
from inference.gradcam import heatmap_stats, overlay
from inference.predictor import prepare_image

REVIEW_STATUS_FOR = {
    REVIEW: "PENDING_REVIEW",            # engine could not decide reliably
    REJECT: "PENDING_CONFIRMATION",      # a person confirms before material is scrapped
    PASS: "NOT_REQUIRED",
}
SAFE_EXT = {".png", ".bmp", ".jpg", ".jpeg", ".tif", ".tiff"}


def _store(rel_path: str, data: bytes) -> str:
    p = settings.storage_dir / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return rel_path


def new_product_id() -> str:
    return f"P-{uuid.uuid4().hex[:8].upper()}"


def run_inspection(db, image_bytes: bytes, *, product_id: str | None, batch_id: str | None,
                   source_reference: str, model_key: str | None = None, ground_truth: str | None = None,
                   sequence_no: int | None = None) -> Inspection:
    t0 = time.perf_counter()
    bundle = registry.get(model_key)
    prepared = prepare_image(image_bytes)                  # raises ValueError for undecodable files
    with registry.lock:
        pred = bundle.predict(prepared)
        heat, _ = bundle.gradcam.compute(prepared.gray, pred.class_index)
    decision = registry.engine.decide_prediction(pred)

    iid = str(uuid.uuid4())
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ext = Path(source_reference).suffix.lower()
    ext = ext if ext in SAFE_EXT else ".img"
    original = _store(f"originals/{day}/{iid}{ext}", image_bytes)
    model_input = _store(f"inputs/{day}/{iid}.png", cv2.imencode(".png", prepared.gray)[1].tobytes())
    cam_path = _store(f"gradcam/{day}/{iid}.png", cv2.imencode(".png", overlay(prepared.gray, heat))[1].tobytes())
    processing_ms = (time.perf_counter() - t0) * 1000

    insp = Inspection(
        inspection_id=iid, product_id=product_id or new_product_id(), batch_id=batch_id,
        sequence_no=sequence_no, image_path=model_input, original_path=original,
        source_reference=source_reference, image_sha256=hashlib.sha256(image_bytes).hexdigest(),
        ground_truth=ground_truth, processing_ms=round(processing_ms, 2),
        review_status=REVIEW_STATUS_FOR[decision.decision],
    )
    insp.prediction = Prediction(
        model_version_id=registry.model_ids[bundle.key], predicted_class=pred.predicted_class,
        confidence=pred.confidence, margin=pred.margin, normalized_entropy=pred.normalized_entropy,
        probabilities=pred.probabilities, input_flags=pred.input_flags, latency_ms=pred.latency_ms,
        gradcam_path=cam_path, gradcam_layer=bundle.gradcam_layer, gradcam_stats=heatmap_stats(heat),
    )
    insp.decision = Decision(
        decision=decision.decision, rule_fired=decision.rule_fired, reasons=decision.reasons,
        policy_version=decision.policy_version, policy_snapshot=registry.policy.to_dict(),
    )
    db.add(insp)
    db.commit()
    return insp
