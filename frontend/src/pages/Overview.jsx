import { Link } from "react-router-dom";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api.js";
import { AcademicNotice, ClassLabel, DecisionBadge, Empty, ErrorMsg, Kpi, Loading, ReviewBadge, useApi } from "../components/ui.jsx";
import { CLASS_COLORS, DECISIONS, DECISION_HEX, DECISION_META, fmtTime, ms, pct, pretty } from "../constants.js";

export default function Overview() {
  const { data, error, loading } = useApi(() => api.overview());
  if (loading && !data) return <Loading />;
  if (error) return <ErrorMsg error={error} />;
  const t = data.totals;
  const total = t.inspections;
  const dc = data.decision_counts;
  const defects = Object.entries(data.defect_counts).map(([name, value]) => ({ name, value }));

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Factory Overview</h1>
          <p>Live summary of every inspection stored in the database. Model <code>{data.default_model}</code> · decision policy v{data.policy_version}.</p>
        </div>
        <div className="row">
          <Link className="btn primary" to="/app/inspect">Inspect image</Link>
          <Link className="btn" to="/app/batch">Run line simulation</Link>
        </div>
      </div>

      {total === 0 ? (
        <div className="card"><Empty>No inspections yet. Inspect an image or run a simulated batch to populate the dashboard.</Empty></div>
      ) : (
        <div className="grid" style={{ gap: 16 }}>
          <div className="grid g6">
            <Kpi accent label="Inspections" value={total} sub={`${t.last_24h} in last 24 h · ${t.batches} batches`} />
            {DECISIONS.map((d) => (
              <Kpi key={d} label={DECISION_META[d].label} value={dc[d]} sub={pct(dc[d] / total)} />
            ))}
            <Kpi label="Review backlog" value={t.pending_review + t.pending_confirmation}
                 sub={`${t.pending_review} review · ${t.pending_confirmation} confirm`} />
            <Kpi label="Avg processing" value={ms(data.avg_processing_ms, 0)} sub={`model ${ms(data.avg_model_latency_ms, 1)}`} />
          </div>

          <div className="grid g3">
            <div className="card span2">
              <h2>Decisions over time (per {data.timeline_granularity})</h2>
              <ResponsiveContainer width="100%" height={240}>
                <AreaChart data={data.timeline}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="bucket" tick={{ fontSize: 10 }} />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Legend formatter={(v) => DECISION_META[v]?.label || v} />
                  {DECISIONS.map((d) => (
                    <Area key={d} type="monotone" dataKey={d} stackId="1" stroke={DECISION_HEX[d]} fill={DECISION_HEX[d]} fillOpacity={0.35} />
                  ))}
                </AreaChart>
              </ResponsiveContainer>
            </div>
            <div className="card">
              <h2>Predicted defect types</h2>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={defects} layout="vertical" margin={{ left: 30 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <XAxis type="number" allowDecimals={false} />
                  <YAxis type="category" dataKey="name" width={100} tickFormatter={pretty} />
                  <Tooltip formatter={(v) => [v, "inspections"]} labelFormatter={pretty} />
                  <Bar dataKey="value">{defects.map((d) => <Cell key={d.name} fill={CLASS_COLORS[d.name]} />)}</Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="card">
            <div className="row" style={{ marginBottom: 8 }}><h2 style={{ margin: 0 }}>Most recent inspections</h2><span className="spacer" /><Link to="/app/history">All history →</Link></div>
            <div className="table-wrap">
              <table>
                <thead><tr><th></th><th>Time</th><th>Product</th><th>Batch</th><th>Predicted defect</th><th className="num">Confidence</th><th>Decision</th><th>Review</th></tr></thead>
                <tbody>
                  {data.recent.map((r) => (
                    <tr key={r.inspection_id}>
                      <td><img className="thumb" src={r.image_url} alt="" /></td>
                      <td className="small" style={{ whiteSpace: "nowrap" }}>{fmtTime(r.timestamp)}</td>
                      <td className="mono small ellipsis" title={r.product_id}>{r.product_id}</td>
                      <td className="mono small ellipsis" title={r.batch_id || ""}>{r.batch_id || "—"}</td>
                      <td><ClassLabel name={r.predicted_class} /></td>
                      <td className="num">{pct(r.confidence)}</td>
                      <td><DecisionBadge decision={r.decision} /></td>
                      <td><ReviewBadge status={r.review_status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
      <div style={{ marginTop: 16 }}><AcademicNotice /></div>
    </>
  );
}
