import { useState } from "react";
import { api } from "../api.js";
import { CLASSES, fmtTime, ms, pct, pretty } from "../constants.js";
import { ClassLabel, DecisionBadge, ErrorMsg, ProbabilityBars, ReviewBadge } from "./ui.jsx";

function Field({ k, v }) {
  return (
    <>
      <div className="muted small">{k}</div>
      <div className="small" style={{ wordBreak: "break-all" }}>{v}</div>
    </>
  );
}

export default function InspectionDetail({ data, onReviewed }) {
  const d = data;
  return (
    <div className="grid" style={{ gap: 14 }}>
      <div className="row" style={{ alignItems: "center" }}>
        <h3 style={{ margin: 0, fontSize: 18 }}><ClassLabel name={d.predicted_class} /></h3>
        <span className="mono" style={{ fontSize: 18 }}>{pct(d.confidence, 2)}</span>
        <DecisionBadge decision={d.decision} />
        <ReviewBadge status={d.review_status} />
        <span className="spacer" />
        <a className="btn" href={api.inspectionPdfUrl(d.inspection_id)}>PDF report</a>
      </div>

      <div className="img-pair">
        <div className="img-box">
          <img src={d.image_url} alt="Inspected steel surface (model input)" />
          <div className="img-cap">Original — model input, 200×200 grayscale</div>
        </div>
        <div className="img-box">
          <img src={d.gradcam_url} alt="Grad-CAM heatmap overlay" />
          <div className="img-cap">Grad-CAM heatmap · layer <code>{d.gradcam_layer}</code></div>
        </div>
      </div>
      <div className="notice"><strong>About the heatmap:</strong> {d.gradcam_caveat}</div>

      <div className="grid g2">
        <div className="card tight">
          <h2>Class probabilities</h2>
          <ProbabilityBars probabilities={d.probabilities} predicted={d.predicted_class} />
          <div className="small muted" style={{ marginTop: 8 }}>
            top-1/top-2 margin {d.margin.toFixed(3)} · normalised entropy {d.normalized_entropy.toFixed(3)}
          </div>
        </div>
        <div className="card tight">
          <h2>Decision engine</h2>
          <div className="small"><span className="muted">Rule fired:</span> <code>{d.rule_fired}</code></div>
          <ul className="small" style={{ paddingLeft: 18, margin: "8px 0" }}>
            {d.decision_reasons.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
          {d.input_flags.length > 0 && (
            <div className="notice warn small">Input flags: {d.input_flags.map(pretty).join(", ")}</div>
          )}
          <div className="small muted">Policy v{d.policy_version} · decided {fmtTime(d.decided_at)}</div>
        </div>
      </div>

      <div className="card tight">
        <h2>Inspection record</h2>
        <div style={{ display: "grid", gridTemplateColumns: "140px 1fr", gap: "4px 12px" }}>
          <Field k="Inspection ID" v={<code>{d.inspection_id}</code>} />
          <Field k="Product ID" v={d.product_id} />
          <Field k="Batch ID" v={d.batch_id || "—"} />
          <Field k="Image reference" v={d.image_reference} />
          <Field k="Model version" v={d.model_version} />
          <Field k="Timestamp" v={fmtTime(d.timestamp)} />
          <Field k="Processing time" v={`${ms(d.processing_ms)} end-to-end · ${ms(d.model_latency_ms, 2)} model`} />
          {d.ground_truth && <Field k="Dataset label" v={<>{pretty(d.ground_truth)} <span className="muted">(simulation only)</span></>} />}
          <Field k="Image SHA-256" v={<code>{d.image_sha256}</code>} />
        </div>
      </div>

      <ReviewPanel d={d} onReviewed={onReviewed} />
    </div>
  );
}

function ReviewPanel({ d, onReviewed }) {
  const suggested = { PASS_CANDIDATE: "PASS", REJECT_CANDIDATE: "REJECT" }[d.decision] || "HOLD";
  const [form, setForm] = useState({ reviewer: "", final_disposition: suggested, corrected_class: "", notes: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setError(null);
    try {
      const res = await api.review(d.inspection_id, { ...form, corrected_class: form.corrected_class || null });
      onReviewed && onReviewed(res);
    } catch (err) { setError(err); } finally { setBusy(false); }
  };

  return (
    <div className="card tight">
      <h2>Human review</h2>
      {d.reviews.length > 0 && (
        <div className="table-wrap" style={{ marginBottom: 12 }}>
          <table>
            <thead><tr><th>When</th><th>Reviewer</th><th>Outcome</th><th>Disposition</th><th>Corrected class</th><th>Notes</th></tr></thead>
            <tbody>
              {d.reviews.map((r, i) => (
                <tr key={i}>
                  <td className="small">{fmtTime(r.reviewed_at)}</td><td>{r.reviewer}</td><td>{r.outcome}</td>
                  <td>{r.final_disposition}</td><td>{r.corrected_class ? pretty(r.corrected_class) : "—"}</td><td className="small">{r.notes}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <form onSubmit={submit} className="row">
        <label className="field">Reviewer<input required value={form.reviewer} onChange={set("reviewer")} placeholder="name / badge" /></label>
        <label className="field">Final disposition
          <select value={form.final_disposition} onChange={set("final_disposition")}>
            <option>PASS</option><option>REJECT</option><option>HOLD</option>
          </select>
        </label>
        <label className="field">Corrected class (optional)
          <select value={form.corrected_class} onChange={set("corrected_class")}>
            <option value="">— keep model class —</option>
            {CLASSES.map((c) => <option key={c} value={c}>{pretty(c)}</option>)}
          </select>
        </label>
        <label className="field" style={{ flex: 1, minWidth: 180 }}>Notes<input value={form.notes} onChange={set("notes")} /></label>
        <button className="primary" disabled={busy}>{busy ? "Saving…" : "Record review"}</button>
      </form>
      <ErrorMsg error={error} />
      <div className="small muted" style={{ marginTop: 6 }}>Reviews are stored separately; the model prediction and engine decision are never modified.</div>
    </div>
  );
}
