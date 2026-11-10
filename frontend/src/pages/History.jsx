import { useState } from "react";
import { api } from "../api.js";
import InspectionDetail from "../components/InspectionDetail.jsx";
import { ClassLabel, DecisionBadge, Empty, ErrorMsg, Loading, ReviewBadge, useApi } from "../components/ui.jsx";
import { CLASSES, DECISIONS, DECISION_META, REVIEW_STATUS, fmtTime, ms, pct, pretty } from "../constants.js";

const PAGE = 25;
const EMPTY = { search: "", batch_id: "", decision: "", review_status: "", predicted_class: "", model: "" };

export default function History() {
  const models = useApi(() => api.models());
  const [filters, setFilters] = useState(EMPTY);
  const [applied, setApplied] = useState(EMPTY);
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState(null);
  const list = useApi(() => api.inspections({ ...applied, limit: PAGE, offset }), [applied, offset]);
  const set = (k) => (e) => setFilters({ ...filters, [k]: e.target.value });

  const open = async (id) => {
    try { setSelected(await api.inspection(id)); } catch (e) { alert(e.message); }
  };

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Inspection History</h1>
          <p>Every inspection with its prediction, engine decision and human review status. Click a row to open it and record a review.</p>
        </div>
        <a className="btn" href={api.csvUrl(applied)}>Export CSV (current filters)</a>
      </div>

      <form className="card row" style={{ marginBottom: 16 }} onSubmit={(e) => { e.preventDefault(); setOffset(0); setApplied(filters); }}>
        <label className="field" style={{ minWidth: 200 }}>Search (ID, product, file)<input value={filters.search} onChange={set("search")} /></label>
        <label className="field">Batch ID<input value={filters.batch_id} onChange={set("batch_id")} /></label>
        <label className="field">Predicted defect
          <select value={filters.predicted_class} onChange={set("predicted_class")}>
            <option value="">All</option>{CLASSES.map((c) => <option key={c} value={c}>{pretty(c)}</option>)}
          </select>
        </label>
        <label className="field">Decision
          <select value={filters.decision} onChange={set("decision")}>
            <option value="">All</option>{DECISIONS.map((d) => <option key={d} value={d}>{DECISION_META[d].label}</option>)}
          </select>
        </label>
        <label className="field">Review status
          <select value={filters.review_status} onChange={set("review_status")}>
            <option value="">All</option>{Object.entries(REVIEW_STATUS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </label>
        <label className="field">Model
          <select value={filters.model} onChange={set("model")}>
            <option value="">All</option>{(models.data || []).map((m) => <option key={m.key} value={m.key}>{m.key}</option>)}
          </select>
        </label>
        <button className="primary">Apply</button>
        <button type="button" onClick={() => { setFilters(EMPTY); setApplied(EMPTY); setOffset(0); }}>Reset</button>
      </form>

      <div className="card">
        {list.loading && !list.data ? <Loading /> : list.error ? <ErrorMsg error={list.error} /> : list.data.total === 0 ? (
          <Empty>No inspections match these filters.</Empty>
        ) : (
          <>
            <div className="table-wrap">
              <table>
                <thead><tr><th></th><th>Timestamp</th><th>Inspection ID</th><th>Product</th><th>Batch</th><th>Image reference</th><th>Predicted defect</th><th className="num">Confidence</th><th>Model</th><th>Decision</th><th>Review</th><th className="num">Time</th></tr></thead>
                <tbody>
                  {list.data.items.map((r) => (
                    <tr key={r.inspection_id} className="clickable" onClick={() => open(r.inspection_id)}>
                      <td><img className="thumb" src={r.image_url} alt="" /></td>
                      <td className="small" style={{ whiteSpace: "nowrap" }}>{fmtTime(r.timestamp)}</td>
                      <td className="mono small">{r.inspection_id.slice(0, 8)}</td>
                      <td className="mono small ellipsis" title={r.product_id}>{r.product_id}</td>
                      <td className="mono small ellipsis" title={r.batch_id || ""}>{r.batch_id || "—"}</td>
                      <td className="small" title={r.image_reference} style={{ maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.image_reference}</td>
                      <td><ClassLabel name={r.predicted_class} /></td>
                      <td className="num">{pct(r.confidence)}</td>
                      <td className="mono small">{r.model_version}</td>
                      <td><DecisionBadge decision={r.decision} /></td>
                      <td><ReviewBadge status={r.review_status} /></td>
                      <td className="num">{ms(r.processing_ms, 0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="row" style={{ marginTop: 12, alignItems: "center" }}>
              <span className="muted small">{offset + 1}–{Math.min(offset + PAGE, list.data.total)} of {list.data.total}</span>
              <span className="spacer" />
              <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE))}>← Prev</button>
              <button disabled={offset + PAGE >= list.data.total} onClick={() => setOffset(offset + PAGE)}>Next →</button>
            </div>
          </>
        )}
      </div>

      {selected && (
        <>
          <div className="drawer-bg" onClick={() => setSelected(null)} />
          <div className="drawer" role="dialog" aria-label="Inspection detail">
            <div className="row" style={{ marginBottom: 12 }}>
              <h1>Inspection {selected.inspection_id.slice(0, 8)}</h1><span className="spacer" />
              <button onClick={() => setSelected(null)}>Close</button>
            </div>
            <InspectionDetail data={selected} onReviewed={(d) => { setSelected(d); list.reload(); }} />
          </div>
        </>
      )}
    </>
  );
}
