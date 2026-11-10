"""Batch inspection and simulated production-line playback.

A batch is a queue of images processed strictly one after another. `run_batch` is a generator that
yields one event per inspected image, used by the Server-Sent-Events endpoint so the dashboard can
show the inspection sequence live.

SIMULATION NOTICE: the "production line" is a sequential playback of stored images (uploaded files
or held-out NEU-CLS test images). `pacing_ms` only inserts a pause between images to make the
sequence observable; there is no camera, conveyor, PLC or hardware integration.
"""
from __future__ import annotations

import time
import uuid
from collections import Counter
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sqlalchemy import select

from backend.database.models import Batch, BatchItem, Inspection, utcnow
from backend.services.inspection import run_inspection
from backend.services.serializers import inspection_dict
from backend.settings import PROJECT_ROOT, settings
from ml.utils.config import load_config

SIMULATION_NOTICE = ("Simulated production-line playback of stored images. No camera, conveyor or "
                     "hardware integration; timings are CPU software timings on this machine.")


def new_batch_id(prefix: str = "B") -> str:
    return f"{prefix}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"


def create_upload_batch(db, files: list[tuple[str, bytes]], product_line: str | None, model_key: str,
                        pacing_ms: int, product_prefix: str | None) -> Batch:
    b = Batch(batch_id=new_batch_id("B"), product_line=product_line, source="upload",
              model_key=model_key, pacing_ms=pacing_ms)
    db.add(b)
    for seq, (name, data) in enumerate(files, start=1):
        staged = settings.storage_dir / "staging" / b.batch_id / f"{seq:04d}"
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_bytes(data)
        b.items.append(BatchItem(sequence_no=seq, source_reference=name,
                                 staged_path=str(staged.relative_to(settings.storage_dir).as_posix()),
                                 product_id=f"{product_prefix or b.batch_id}-{seq:04d}"))
    db.commit()
    return b


def create_simulation_batch(db, n_images: int, seed: int, model_key: str, pacing_ms: int,
                            product_line: str | None) -> Batch:
    """Sample images from the held-out TEST split (never used for training or tuning)."""
    cfg = load_config(settings.data_config)
    test = pd.read_csv(PROJECT_ROOT / cfg["split"]["out_dir"] / "test.csv")
    n = min(n_images, len(test))
    rows = test.iloc[np.random.default_rng(seed).permutation(len(test))[:n]]
    b = Batch(batch_id=new_batch_id("SIM"), product_line=product_line or "Simulated line", source="simulation",
              model_key=model_key, pacing_ms=pacing_ms,
              notes=f"{n} images sampled (seed={seed}) from the held-out NEU-CLS test split. {SIMULATION_NOTICE}")
    db.add(b)
    for seq, r in enumerate(rows.itertuples(), start=1):
        b.items.append(BatchItem(sequence_no=seq, source_reference=r.filepath, staged_path=None,
                                 ground_truth=r.label, product_id=f"{b.batch_id}-{seq:04d}"))
    db.commit()
    return b


def _read_item(item: BatchItem) -> bytes:
    if item.staged_path:
        return (settings.storage_dir / item.staged_path).read_bytes()
    return (PROJECT_ROOT / item.source_reference).read_bytes()


def run_batch(db, batch_id: str):
    """Process pending items sequentially; yields ('inspection'|'item_error'|'summary', payload)."""
    b = db.get(Batch, batch_id)
    if b is None:
        raise KeyError(batch_id)
    if b.status == "running":
        raise RuntimeError("Batch is already running")
    b.status, b.started_at = "running", b.started_at or utcnow()
    db.commit()
    pending = [it for it in b.items if it.status == "pending"]
    t_batch = time.perf_counter()
    try:
        for idx, item in enumerate(pending):
            try:
                insp = run_inspection(db, _read_item(item), product_id=item.product_id, batch_id=b.batch_id,
                                      source_reference=item.source_reference, model_key=b.model_key,
                                      ground_truth=item.ground_truth, sequence_no=item.sequence_no)
                item.status, item.inspection_id = "done", insp.inspection_id
                if item.staged_path:
                    (settings.storage_dir / item.staged_path).unlink(missing_ok=True)
                db.commit()
                ev = inspection_dict(insp, full=False)
                ev["gradcam_url"] = f"/storage/{insp.prediction.gradcam_path}"
                ev["progress"] = {"done": idx + 1, "total": len(pending)}
                yield "inspection", ev
            except Exception as e:  # one bad file must not stop the line
                item.status, item.error = "failed", str(e)[:500]
                db.commit()
                yield "item_error", {"sequence_no": item.sequence_no, "source_reference": item.source_reference,
                                "error": item.error, "progress": {"done": idx + 1, "total": len(pending)}}
            if b.pacing_ms and idx < len(pending) - 1:
                time.sleep(b.pacing_ms / 1000)
        b.status = "completed"
    except GeneratorExit:   # client disconnected: leave remaining items pending
        b.status = "queued"
        db.commit()
        raise
    except Exception:
        b.status = "failed"
        raise
    finally:
        if b.status != "queued":
            b.finished_at = utcnow()
        db.commit()
    yield "summary", batch_summary(db, batch_id, wall_seconds=time.perf_counter() - t_batch)


def batch_summary(db, batch_id: str, wall_seconds: float | None = None) -> dict:
    b = db.get(Batch, batch_id)
    insps = db.scalars(select(Inspection).where(Inspection.batch_id == batch_id).order_by(Inspection.sequence_no)).all()
    proc = np.array([i.processing_ms for i in insps]) if insps else np.array([])
    lat = np.array([i.prediction.latency_ms for i in insps]) if insps else np.array([])
    summary = {
        "batch_id": b.batch_id, "source": b.source, "status": b.status, "model_key": b.model_key,
        "product_line": b.product_line, "n_items": len(b.items), "n_inspected": len(insps),
        "n_failed": sum(it.status == "failed" for it in b.items),
        "decision_counts": dict(Counter(i.decision.decision for i in insps)),
        "defect_counts": dict(Counter(i.prediction.predicted_class for i in insps)),
        "review_status_counts": dict(Counter(i.review_status for i in insps)),
        "processing_ms": {"mean": float(proc.mean()), "median": float(np.median(proc)), "max": float(proc.max())} if len(proc) else None,
        "model_latency_ms": {"mean": float(lat.mean()), "median": float(np.median(lat))} if len(lat) else None,
        "notice": SIMULATION_NOTICE,
    }
    if wall_seconds is not None and insps:
        summary["wall_seconds"] = round(wall_seconds, 2)
    labelled = [i for i in insps if i.ground_truth]
    if labelled:
        summary["ground_truth_agreement"] = {
            "n": len(labelled),
            "accuracy": sum(i.prediction.predicted_class == i.ground_truth for i in labelled) / len(labelled),
            "note": "Only available for simulation batches drawn from the labelled NEU-CLS test split.",
        }
    return summary
