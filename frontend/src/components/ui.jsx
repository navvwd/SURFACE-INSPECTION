import { useEffect, useState } from "react";
import { CLASS_COLORS, DECISION_META, REVIEW_STATUS, pretty } from "../constants.js";

export function Kpi({ label, value, sub, accent }) {
  return (
    <div className={`card kpi${accent ? " accent" : ""}`}>
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {sub && <div className="sub">{sub}</div>}
    </div>
  );
}

export function DecisionBadge({ decision }) {
  const m = DECISION_META[decision];
  if (!m) return <span className="chip">{decision}</span>;
  return <span className="badge" style={{ color: m.color }}>{m.label}</span>;
}

export function ReviewBadge({ status }) {
  const color = { PENDING_REVIEW: "var(--review)", PENDING_CONFIRMATION: "var(--reject)", REVIEWED: "var(--pass)" }[status] || "var(--muted)";
  return <span className="badge plain" style={{ color, borderColor: "var(--line)" }}>{REVIEW_STATUS[status] || status}</span>;
}

export function ClassLabel({ name }) {
  return (
    <span style={{ whiteSpace: "nowrap" }}>
      <span className="dot" style={{ background: CLASS_COLORS[name] || "var(--muted)" }} />
      {pretty(name)}
    </span>
  );
}

export function ProbabilityBars({ probabilities, predicted }) {
  const entries = Object.entries(probabilities || {}).sort((a, b) => b[1] - a[1]);
  return (
    <div>
      {entries.map(([c, p]) => (
        <div className="prob" key={c}>
          <span style={{ fontWeight: c === predicted ? 600 : 400 }}><ClassLabel name={c} /></span>
          <div className="bar"><span style={{ width: `${Math.max(p * 100, 0.5)}%`, background: CLASS_COLORS[c] }} /></div>
          <span className="mono" style={{ textAlign: "right" }}>{(p * 100).toFixed(2)}%</span>
        </div>
      ))}
    </div>
  );
}

export function Loading({ what = "Loading" }) {
  return <div className="muted small">{what}…</div>;
}

export function ErrorMsg({ error }) {
  return error ? <div className="error">⚠ {String(error.message || error)}</div> : null;
}

export function Empty({ children }) {
  return <div className="muted" style={{ padding: "24px 0", textAlign: "center" }}>{children}</div>;
}

export function AcademicNotice() {
  return (
    <div className="notice warn">
      <strong>Academic prototype.</strong> The model was trained on the NEU-CLS benchmark (6 defect types, no
      defect-free class). Benchmark accuracy does not predict performance on a real production line, and every
      outcome is a <em>candidate</em> for human disposition.
    </div>
  );
}

/** Small data-loading hook: returns {data, error, loading, reload}. */
export function useApi(fn, deps = []) {
  const [state, set] = useState({ data: null, error: null, loading: true });
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let alive = true;
    set((s) => ({ ...s, loading: true }));
    fn()
      .then((data) => alive && set({ data, error: null, loading: false }))
      .catch((error) => alive && set({ data: null, error, loading: false }));
    return () => { alive = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);
  return { ...state, reload: () => setTick((t) => t + 1) };
}

export function ModelSelect({ models, value, onChange }) {
  return (
    <label className="field">
      Model
      <select value={value || ""} onChange={(e) => onChange(e.target.value)}>
        {(models || []).map((m) => (
          <option key={m.key} value={m.key}>
            {m.key}{m.is_default ? " (default)" : ""}
          </option>
        ))}
      </select>
    </label>
  );
}
