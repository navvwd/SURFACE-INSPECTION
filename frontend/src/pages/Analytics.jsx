import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api.js";
import { Empty, ErrorMsg, Kpi, Loading, useApi } from "../components/ui.jsx";
import { CLASSES, CLASS_COLORS, DECISIONS, DECISION_HEX, DECISION_META, pct, pretty } from "../constants.js";

export default function Analytics() {
  const batches = useApi(() => api.batches());
  const [batchId, setBatchId] = useState("");
  const { data, error, loading } = useApi(() => api.defects({ batch_id: batchId }), [batchId]);

  const header = (
    <div className="page-head">
      <div>
        <h1>Defect Analytics</h1>
        <p>Distribution of predicted defect types, how the decision policy treated them, and confidence behaviour. All figures are aggregated from stored inspections.</p>
      </div>
      <label className="field">Scope
        <select value={batchId} onChange={(e) => setBatchId(e.target.value)}>
          <option value="">All inspections</option>
          {(batches.data || []).map((b) => <option key={b.batch_id} value={b.batch_id}>{b.batch_id} ({b.n_done})</option>)}
        </select>
      </label>
    </div>
  );
  if (loading && !data) return <>{header}<Loading /></>;
  if (error) return <>{header}<ErrorMsg error={error} /></>;
  if (!data.n) return <>{header}<div className="card"><Empty>No inspections in this scope yet.</Empty></div></>;

  const matrix = CLASSES.map((c) => ({ name: c, ...(data.class_decision_matrix[c] || {}) }));
  const confData = data.confidence_histogram.bins.map((bin, k) => {
    const row = { bin };
    CLASSES.forEach((c) => { row[c] = data.confidence_histogram.counts[c]?.[k] || 0; });
    return row;
  });
  const rules = Object.entries(data.rule_counts).sort((a, b) => b[1] - a[1]).map(([rule, n]) => ({ rule, n }));
  const sim = data.simulation_ground_truth;

  return (
    <>
      {header}
      <div className="grid" style={{ gap: 16 }}>
        <div className="grid g4">
          <Kpi accent label="Inspections in scope" value={data.n} />
          <Kpi label="Human reviews recorded" value={Object.values(data.review_outcomes).reduce((a, b) => a + b, 0)}
               sub={Object.entries(data.review_outcomes).map(([k, v]) => `${k.toLowerCase()} ${v}`).join(" · ") || "none yet"} />
          <Kpi label="Inputs flagged" value={Object.values(data.input_flag_counts).reduce((a, b) => a + b, 0)}
               sub={Object.entries(data.input_flag_counts).map(([k, v]) => `${pretty(k)} ${v}`).join(" · ") || "none"} />
          <Kpi label="Label agreement (simulation)" value={sim.accuracy === null ? "—" : pct(sim.accuracy)} sub={`n=${sim.n} labelled test images`} />
        </div>

        <div className="grid g2">
          <div className="card">
            <h2>Predicted defect × inspection decision</h2>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={matrix}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" tickFormatter={pretty} interval={0} tick={{ fontSize: 10 }} />
                <YAxis allowDecimals={false} />
                <Tooltip labelFormatter={pretty} formatter={(v, k) => [v, DECISION_META[k]?.label || k]} />
                <Legend formatter={(v) => DECISION_META[v]?.label || v} />
                {DECISIONS.map((d) => <Bar key={d} dataKey={d} stackId="a" fill={DECISION_HEX[d]} />)}
              </BarChart>
            </ResponsiveContainer>
            <div className="small muted">Decisions follow the configured class policy plus uncertainty gates; see the Model Performance page for the active policy.</div>
          </div>
          <div className="card">
            <h2>Confidence distribution by predicted class</h2>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={confData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="bin" tick={{ fontSize: 10 }} />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Legend formatter={pretty} />
                {CLASSES.map((c) => <Bar key={c} dataKey={c} stackId="c" fill={CLASS_COLORS[c]} />)}
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="grid g2">
          <div className="card">
            <h2>Decision rules fired</h2>
            <ResponsiveContainer width="100%" height={Math.max(160, rules.length * 34)}>
              <BarChart data={rules} layout="vertical" margin={{ left: 60 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" allowDecimals={false} />
                <YAxis type="category" dataKey="rule" width={190} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="n" fill="#4e9fd1">{rules.map((r) => <Cell key={r.rule} fill={r.rule.includes("reject") && !r.rule.includes("needs") ? DECISION_HEX.REJECT_CANDIDATE : r.rule.includes("accept") ? DECISION_HEX.PASS_CANDIDATE : DECISION_HEX.MANUAL_REVIEW} />)}</Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="card">
            <h2>Mean confidence by predicted class</h2>
            <table>
              <thead><tr><th>Class</th><th className="num">Predicted</th><th className="num">Mean confidence</th><th className="num">Sent to review</th></tr></thead>
              <tbody>
                {CLASSES.map((c) => {
                  const row = data.class_decision_matrix[c] || {};
                  const n = DECISIONS.reduce((a, d) => a + (row[d] || 0), 0);
                  return (
                    <tr key={c}>
                      <td><span className="dot" style={{ background: CLASS_COLORS[c] }} />{pretty(c)}</td>
                      <td className="num">{n}</td>
                      <td className="num">{data.mean_confidence_by_class[c] !== undefined ? pct(data.mean_confidence_by_class[c]) : "—"}</td>
                      <td className="num">{n ? pct((row.MANUAL_REVIEW || 0) / n, 0) : "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {data.per_batch.length > 0 && (
          <div className="card">
            <h2>Per-batch breakdown</h2>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Batch</th><th className="num">Total</th>{CLASSES.map((c) => <th key={c} className="num">{pretty(c)}</th>)}{DECISIONS.map((d) => <th key={d} className="num">{DECISION_META[d].short}</th>)}</tr></thead>
                <tbody>
                  {data.per_batch.map((b) => (
                    <tr key={b.batch_id}>
                      <td className="mono small">{b.batch_id}</td><td className="num">{b.total}</td>
                      {CLASSES.map((c) => <td key={c} className="num">{b[c]}</td>)}
                      {DECISIONS.map((d) => <td key={d} className="num" style={{ color: DECISION_HEX[d] }}>{b[d]}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
