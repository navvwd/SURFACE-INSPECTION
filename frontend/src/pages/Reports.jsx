import { useState } from "react";
import { api } from "../api.js";
import { Empty, ErrorMsg, Loading, useApi } from "../components/ui.jsx";
import { CLASSES, DECISIONS, DECISION_META, REVIEW_STATUS, fmtTime, pretty } from "../constants.js";

export default function Reports() {
  const batches = useApi(() => api.batches());
  const [f, setF] = useState({ batch_id: "", decision: "", review_status: "", predicted_class: "", date_from: "", date_to: "" });
  const [inspId, setInspId] = useState("");
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Exportable Inspection Reports</h1>
          <p>CSV exports for spreadsheets and quality systems; PDF reports for batches and individual inspections. Every report carries the academic-prototype disclaimer.</p>
        </div>
      </div>
      <div className="grid g2" style={{ alignItems: "start" }}>
        <div className="card">
          <h2>Inspection history → CSV</h2>
          <div className="row">
            <label className="field">Batch<select value={f.batch_id} onChange={set("batch_id")}>
              <option value="">All</option>{(batches.data || []).map((b) => <option key={b.batch_id}>{b.batch_id}</option>)}
            </select></label>
            <label className="field">Decision<select value={f.decision} onChange={set("decision")}>
              <option value="">All</option>{DECISIONS.map((d) => <option key={d} value={d}>{DECISION_META[d].label}</option>)}
            </select></label>
            <label className="field">Review status<select value={f.review_status} onChange={set("review_status")}>
              <option value="">All</option>{Object.entries(REVIEW_STATUS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select></label>
            <label className="field">Predicted defect<select value={f.predicted_class} onChange={set("predicted_class")}>
              <option value="">All</option>{CLASSES.map((c) => <option key={c} value={c}>{pretty(c)}</option>)}
            </select></label>
            <label className="field">From (UTC)<input type="datetime-local" value={f.date_from} onChange={set("date_from")} /></label>
            <label className="field">To (UTC)<input type="datetime-local" value={f.date_to} onChange={set("date_to")} /></label>
          </div>
          <div style={{ marginTop: 12 }}><a className="btn primary" href={api.csvUrl(f)}>Download CSV</a></div>
          <div className="small muted" style={{ marginTop: 8 }}>
            Columns: inspection ID, timestamp, product ID, batch ID, sequence, image reference, predicted defect, confidence, model version,
            decision, rule fired, review status, final disposition, reviewer, processing time, model latency, dataset label (simulation only).
          </div>
        </div>

        <div className="card">
          <h2>Single inspection → PDF</h2>
          <form className="row" onSubmit={(e) => { e.preventDefault(); if (inspId.trim()) window.location.href = api.inspectionPdfUrl(inspId.trim()); }}>
            <label className="field" style={{ flex: 1 }}>Inspection ID<input value={inspId} onChange={(e) => setInspId(e.target.value)} placeholder="full UUID (copy from History)" /></label>
            <button className="primary" disabled={!inspId.trim()}>Download PDF</button>
          </form>
          <div className="small muted" style={{ marginTop: 8 }}>Includes image, Grad-CAM with caveat, probabilities, decision reasons, policy version and review trail.</div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <h2>Batch reports → PDF</h2>
        {batches.loading ? <Loading /> : batches.error ? <ErrorMsg error={batches.error} /> : batches.data.length === 0 ? <Empty>No batches yet.</Empty> : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Batch ID</th><th>Source</th><th>Product line</th><th>Model</th><th>Status</th><th className="num">Done / items</th><th>Created</th><th></th></tr></thead>
              <tbody>
                {batches.data.map((b) => (
                  <tr key={b.batch_id}>
                    <td className="mono small">{b.batch_id}</td><td>{b.source}</td><td>{b.product_line || "—"}</td>
                    <td className="mono small">{b.model_key}</td><td>{b.status}</td>
                    <td className="num">{b.n_done} / {b.n_items}</td><td className="small">{fmtTime(b.created_at)}</td>
                    <td><a className="btn" href={api.batchPdfUrl(b.batch_id)}>PDF</a> <a className="btn" href={api.csvUrl({ batch_id: b.batch_id })}>CSV</a></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
