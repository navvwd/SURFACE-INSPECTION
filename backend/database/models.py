"""ORM tables.

Model outputs (`predictions`) and inspection outcomes (`decisions`) are separate tables: a decision
records which rule fired under which policy version, and a human `review` records the final
disposition. Nothing downstream ever overwrites what the model actually predicted.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.session import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ModelVersion(Base):
    __tablename__ = "model_versions"
    __table_args__ = (UniqueConstraint("name", "version"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    version: Mapped[str] = mapped_column(String(32))
    artifact_path: Mapped[str] = mapped_column(String(255))
    test_accuracy: Mapped[float | None] = mapped_column(Float)
    test_macro_f1: Mapped[float | None] = mapped_column(Float)
    registered_at: Mapped[datetime] = mapped_column(default=utcnow)


class Batch(Base):
    __tablename__ = "batches"
    batch_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    product_line: Mapped[str | None] = mapped_column(String(128))
    source: Mapped[str] = mapped_column(String(32))            # upload | simulation
    status: Mapped[str] = mapped_column(String(16), default="queued")  # queued|running|completed|failed
    model_key: Mapped[str] = mapped_column(String(64))
    pacing_ms: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]
    items: Mapped[list["BatchItem"]] = relationship(back_populates="batch", order_by="BatchItem.sequence_no")


class BatchItem(Base):
    """Queue entry for sequential (simulated production-line) processing."""
    __tablename__ = "batch_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("batches.batch_id"), index=True)
    sequence_no: Mapped[int] = mapped_column(Integer)
    product_id: Mapped[str] = mapped_column(String(64))
    source_reference: Mapped[str] = mapped_column(String(512))
    staged_path: Mapped[str | None] = mapped_column(String(512))   # uploaded file waiting to be processed
    ground_truth: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="pending")   # pending|done|failed
    error: Mapped[str | None] = mapped_column(Text)
    inspection_id: Mapped[str | None] = mapped_column(String(36))
    batch: Mapped[Batch] = relationship(back_populates="items")


class Inspection(Base):
    __tablename__ = "inspections"
    inspection_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    product_id: Mapped[str] = mapped_column(String(64), index=True)
    batch_id: Mapped[str | None] = mapped_column(ForeignKey("batches.batch_id"), index=True)
    sequence_no: Mapped[int | None] = mapped_column(Integer)
    image_path: Mapped[str] = mapped_column(String(512))           # stored model-input image (relative to storage)
    original_path: Mapped[str] = mapped_column(String(512))        # stored original upload (relative to storage)
    source_reference: Mapped[str] = mapped_column(String(512))     # original file name or dataset path
    image_sha256: Mapped[str] = mapped_column(String(64))
    ground_truth: Mapped[str | None] = mapped_column(String(64))   # only for labelled dataset simulation
    processing_ms: Mapped[float] = mapped_column(Float)            # end-to-end (decode+predict+gradcam+store)
    review_status: Mapped[str] = mapped_column(String(32), index=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)
    prediction: Mapped["Prediction"] = relationship(back_populates="inspection", uselist=False)
    decision: Mapped["Decision"] = relationship(back_populates="inspection", uselist=False)
    reviews: Mapped[list["Review"]] = relationship(back_populates="inspection", order_by="Review.reviewed_at")


class Prediction(Base):
    __tablename__ = "predictions"
    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_id: Mapped[str] = mapped_column(ForeignKey("inspections.inspection_id"), unique=True)
    model_version_id: Mapped[int] = mapped_column(ForeignKey("model_versions.id"))
    predicted_class: Mapped[str] = mapped_column(String(64), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    margin: Mapped[float] = mapped_column(Float)
    normalized_entropy: Mapped[float] = mapped_column(Float)
    probabilities: Mapped[dict] = mapped_column(JSON)
    input_flags: Mapped[list] = mapped_column(JSON)
    latency_ms: Mapped[float] = mapped_column(Float)               # model forward pass only
    gradcam_path: Mapped[str | None] = mapped_column(String(512))
    gradcam_layer: Mapped[str | None] = mapped_column(String(64))
    gradcam_stats: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    inspection: Mapped[Inspection] = relationship(back_populates="prediction")
    model_version: Mapped[ModelVersion] = relationship()


class Decision(Base):
    __tablename__ = "decisions"
    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_id: Mapped[str] = mapped_column(ForeignKey("inspections.inspection_id"), unique=True)
    decision: Mapped[str] = mapped_column(String(32), index=True)
    rule_fired: Mapped[str] = mapped_column(String(64))
    reasons: Mapped[list] = mapped_column(JSON)
    policy_version: Mapped[str] = mapped_column(String(32))
    policy_snapshot: Mapped[dict] = mapped_column(JSON)
    decided_at: Mapped[datetime] = mapped_column(default=utcnow)
    inspection: Mapped[Inspection] = relationship(back_populates="decision")


class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_id: Mapped[str] = mapped_column(ForeignKey("inspections.inspection_id"), index=True)
    reviewer: Mapped[str] = mapped_column(String(128))
    outcome: Mapped[str] = mapped_column(String(32))               # CONFIRMED | OVERRIDDEN
    final_disposition: Mapped[str] = mapped_column(String(16))     # PASS | REJECT | HOLD
    corrected_class: Mapped[str | None] = mapped_column(String(64))
    notes: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime] = mapped_column(default=utcnow)
    inspection: Mapped[Inspection] = relationship(back_populates="reviews")
