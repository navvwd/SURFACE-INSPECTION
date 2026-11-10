"""Exportable inspection reports: CSV (filtered history) and PDF (single inspection, batch)."""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from backend.services.batches import SIMULATION_NOTICE
from backend.settings import settings
from inference.gradcam import CAVEAT

DISCLAIMER = ("Academic prototype. Predictions come from a model trained on the NEU-CLS benchmark (6 defect "
              "types, no defect-free class). Outcomes are candidates for human disposition, not certified "
              "quality decisions. Benchmark accuracy does not predict production-line performance.")

CSV_COLUMNS = ["inspection_id", "timestamp", "product_id", "batch_id", "sequence_no", "image_reference",
               "predicted_class", "confidence", "model_version", "decision", "rule_fired", "review_status",
               "final_disposition", "reviewer", "processing_ms", "model_latency_ms", "ground_truth"]


def inspections_csv(rows: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        last = r.get("reviews")[-1] if r.get("reviews") else {}
        w.writerow({**r, "final_disposition": last.get("final_disposition"), "reviewer": last.get("reviewer")})
    return buf.getvalue()


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle("Small", parent=ss["BodyText"], fontSize=8, leading=10, textColor=colors.HexColor("#444444")))
    return ss


def _table(data, col_widths=None, header=True):
    t = Table(data, colWidths=col_widths, hAlign="LEFT")
    style = [("FONTSIZE", (0, 0), (-1, -1), 8), ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#bbbbbb")),
             ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3b4d")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white)]
    t.setStyle(TableStyle(style))
    return t


def _header(ss, title):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return [Paragraph(f"COCO SurfaceCheck - {title}", ss["Title"]),
            Paragraph("Surface inspection &middot; A COCO MEDIA PRODUCT &middot; <i>Precision in Every Inspection.</i>", ss["Small"]),
            Paragraph(f"Generated {now}", ss["Small"]), Spacer(1, 4 * mm),
            Paragraph(DISCLAIMER, ss["Small"]), Spacer(1, 4 * mm)]


def inspection_pdf(d: dict) -> bytes:
    ss = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=12 * mm)
    el = _header(ss, "Inspection Report")
    meta = [["Inspection ID", d["inspection_id"]], ["Product ID", d["product_id"]], ["Batch ID", d["batch_id"] or "-"],
            ["Timestamp", d["timestamp"]], ["Image reference", d["image_reference"]], ["Model version", d["model_version"]],
            ["Predicted defect", d["predicted_class"]], ["Confidence", f"{d['confidence']:.4f}"],
            ["Top-1/top-2 margin", f"{d['margin']:.4f}"], ["Normalised entropy", f"{d['normalized_entropy']:.4f}"],
            ["Inspection decision", d["decision"]], ["Rule fired", d["rule_fired"]],
            ["Policy version", d["policy_version"]], ["Review status", d["review_status"]],
            ["Input flags", ", ".join(d["input_flags"]) or "none"],
            ["Processing time", f"{d['processing_ms']:.1f} ms (model {d['model_latency_ms']:.1f} ms)"]]
    el.append(_table(meta, [45 * mm, 130 * mm], header=False))
    el.append(Spacer(1, 4 * mm))
    imgs = [Image(str(settings.storage_dir / d["image_url"].removeprefix("/storage/")), 60 * mm, 60 * mm),
            Image(str(settings.storage_dir / d["gradcam_url"].removeprefix("/storage/")), 60 * mm, 60 * mm)]
    el.append(Table([imgs, ["Model input (200x200 gray)", f"Grad-CAM ({d['gradcam_layer']})"]], hAlign="LEFT"))
    el.append(Paragraph(f"<b>Explanation caveat:</b> {CAVEAT}", ss["Small"]))
    el.append(Spacer(1, 3 * mm))
    probs = sorted(d["probabilities"].items(), key=lambda kv: -kv[1])
    el.append(_table([["Class", "Probability"]] + [[c, f"{p:.4f}"] for c, p in probs], [60 * mm, 40 * mm]))
    el.append(Spacer(1, 3 * mm))
    el.append(Paragraph("<b>Decision reasons</b>: " + "; ".join(d["decision_reasons"]), ss["BodyText"]))
    if d["reviews"]:
        el.append(Spacer(1, 3 * mm))
        el.append(_table([["Reviewed at", "Reviewer", "Outcome", "Disposition", "Corrected class", "Notes"]] +
                         [[r["reviewed_at"], r["reviewer"], r["outcome"], r["final_disposition"],
                           r["corrected_class"] or "-", (r["notes"] or "")[:60]] for r in d["reviews"]]))
    doc.build(el)
    return buf.getvalue()


def batch_pdf(summary: dict, rows: list[dict]) -> bytes:
    ss = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm)
    el = _header(ss, f"Batch Report {summary['batch_id']}")
    if summary["source"] == "simulation":
        el += [Paragraph(f"<b>Simulation:</b> {SIMULATION_NOTICE}", ss["Small"]), Spacer(1, 3 * mm)]
    pm = summary.get("processing_ms") or {}
    info = [["Source", summary["source"]], ["Product line", summary.get("product_line") or "-"],
            ["Model", summary["model_key"]], ["Status", summary["status"]],
            ["Images inspected / queued", f"{summary['n_inspected']} / {summary['n_items']} (failed {summary['n_failed']})"],
            ["Decisions", ", ".join(f"{k}: {v}" for k, v in summary["decision_counts"].items()) or "-"],
            ["Predicted defects", ", ".join(f"{k}: {v}" for k, v in summary["defect_counts"].items()) or "-"],
            ["Processing ms (mean / median / max)", f"{pm.get('mean', 0):.1f} / {pm.get('median', 0):.1f} / {pm.get('max', 0):.1f}"]]
    gt = summary.get("ground_truth_agreement")
    if gt:
        info.append(["Agreement with dataset labels", f"{gt['accuracy']:.3f} (n={gt['n']}, simulation only)"])
    el.append(_table(info, [60 * mm, 120 * mm], header=False))
    el.append(Spacer(1, 4 * mm))
    head = ["#", "Product ID", "Predicted", "Conf.", "Decision", "Review status", "ms"]
    if gt:
        head.append("Label")
    data = [head]
    for r in rows:
        line = [r["sequence_no"], r["product_id"], r["predicted_class"], f"{r['confidence']:.3f}",
                r["decision"].replace("_CANDIDATE", ""), r["review_status"], f"{r['processing_ms']:.0f}"]
        if gt:
            line.append(r["ground_truth"] or "")
        data.append(line)
    el.append(_table(data))
    doc.build(el)
    return buf.getvalue()
