import { useEffect, useRef, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api.js";
import { ClassLabel, DecisionBadge, ErrorMsg, Kpi, ModelSelect, useApi } from "../components/ui.jsx";
import { DECISIONS, DECISION_HEX, DECISION_META, ms, pct, pretty } from "../constants.js";

export default function Batch() {
  const models = useApi(() => api.models());
  const [mode, setMode] = useState("simulate");
  const [model, setModel] = useState("");
  const [sim, setSim] = useState({ n_images: 24, seed: 7, pacing_ms: 400, product_line: "Hot-rolled strip line (simulated)" });
  const [files, setFiles] = useState([]);
  const [upl, setUpl] = useState({ productLine: "", productPrefix: "", pacingMs: 0 });
  const [batch, setBatch] = useState(null);
  const [events, setEvents] = useState([]);
  const [errors, setErrors] = useState([]);
  const [summary, setSummary] = useState(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState(null);
  const es = useRef(null);

  useEffect(() => {
    if (!model && models.data?.length) setModel((models.data.find((m) => m.is_default) || models.data[0]).key);
  }, [models.data, model]);
  useEffect(() => () => es.current && es.current.close(), []);

  const start = async () => {
    setError(null); setEvents([]); setErrors([]); setSummary(null);
    try {
      const b = mode === "simulate"
        ? await api.simulate({ ...sim, model })
        : await api.createBatch(files, { ...upl, model });
      setBatch(b);
      stream(b.batch_id);
    } catch (e) { setError(e); }
  };

  const stream = (id) => {
    setRunning(true);
    const source = new EventSource(api.runBatchUrl(id));
    es.current = source;
    source.addEventListener("inspection", (e) => setEvents((prev) => [JSON.parse(e.data), ...prev]));
    source.addEventListener("item_error", (e) => { if (e.data) setErrors((prev) => [JSON.parse(e.data), ...prev]); });
    source.addEventListener("summary", (e) => { setSummary(JSON.parse(e.data)); source.close(); setRunning(false); });
    source.addEventListener("failure", (e) => { setError(new Error(JSON.parse(e.data).error)); source.close(); setRunning(false); });
    source.onerror = () => { source.close(); setRunning(false); };
  };

  const stop = () => { es.current && es.current.close(); setRunning(false); };

  const latest = events[0];
  const total = latest?.progress?.total || batch?.n_items || 0;
  const done = latest?.progress?.done || 0;
  const live = DECISIONS.map((d) => ({ name: d, value: events.filter((e) => e.decision === d).length }));
  const avgProc = events.length ? events.reduce((a, e) => a + e.processing_ms, 0) / events.length : null;
  const labelled = events.filter((e) => e.ground_truth);
  const agree = labelled.length ? labelled.filter((e) => e.ground_truth === e.predicted_class).length / labelled.length : null;

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Batch Inspection & Production-Line Simulation</h1>
          <p>Images are processed strictly one after another and streamed to this page as they complete.</p>
        </div>
      </div>
      <div className="notice warn" style={{ marginBottom: 16 }}>
        <strong>Simulation only.</strong> This is a sequential software playback of stored images. There is no camera, conveyor,
        PLC or hardware integration; pacing is an artificial pause, and timings are CPU software timings on this computer.
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="tabs" style={{ marginBottom: 12 }}>
          <button className={mode === "simulate" ? "on" : ""} onClick={() => setMode("simulate")}>Simulated line (held-out test images)</button>
          <button className={mode === "upload" ? "on" : ""} onClick={() => setMode("upload")}>Upload a batch</button>
        </div>
        {mode === "simulate" ? (
          <div className="row">
            <label className="field">Images (1–270)<input type="number" min={1} max={270} value={sim.n_images} onChange={(e) => setSim({ ...sim, n_images: +e.target.value })} /></label>
            <label className="field">Sampling seed<input type="number" value={sim.seed} onChange={(e) => setSim({ ...sim, seed: +e.target.value })} /></label>
            <label className="field">Pacing between images (ms)<input type="number" min={0} max={5000} step={100} value={sim.pacing_ms} onChange={(e) => setSim({ ...sim, pacing_ms: +e.target.value })} /></label>
            <label className="field" style={{ minWidth: 240 }}>Product line label<input value={sim.product_line} onChange={(e) => setSim({ ...sim, product_line: e.target.value })} /></label>
            <ModelSelect models={models.data} value={model} onChange={setModel} />
            <button className="primary" disabled={running} onClick={start}>Start line</button>
            {running && <button onClick={stop}>Disconnect</button>}
          </div>
        ) : (
          <div className="row">
            <label className="field">Images<input type="file" multiple accept="image/*,.bmp,.tif,.tiff" onChange={(e) => setFiles([...e.target.files])} /></label>
            <label className="field">Product line<input value={upl.productLine} onChange={(e) => setUpl({ ...upl, productLine: e.target.value })} /></label>
            <label className="field">Product ID prefix<input value={upl.productPrefix} placeholder="defaults to batch ID" onChange={(e) => setUpl({ ...upl, productPrefix: e.target.value })} /></label>
            <label className="field">Pacing (ms)<input type="number" min={0} max={5000} step={100} value={upl.pacingMs} onChange={(e) => setUpl({ ...upl, pacingMs: +e.target.value })} /></label>
            <ModelSelect models={models.data} value={model} onChange={setModel} />
            <button className="primary" disabled={running || files.length === 0} onClick={start}>Upload & run ({files.length})</button>
          </div>
        )}
        <ErrorMsg error={error} />
        {mode === "simulate" && (
          <div className="small muted" style={{ marginTop: 8 }}>
            Simulated batches sample the held-out NEU-CLS test split, so the dataset label is known and agreement can be shown.
            Those labels are hidden from the model and the decision engine.
          </div>
        )}
      </div>

      {batch && (
        <div className="grid" style={{ gap: 16 }}>
          <div className="card tight">
            <div className="row" style={{ alignItems: "center" }}>
              <div><span className="muted small">Batch</span> <code>{batch.batch_id}</code> · {batch.product_line || "—"} · <code>{batch.model_key}</code></div>
              <span className="spacer" />
              <span className="mono">{done}/{total}</span>
              {summary && <a className="btn" href={api.batchPdfUrl(batch.batch_id)}>Batch PDF</a>}
            </div>
            <div className="progress" style={{ marginTop: 8 }}><span style={{ width: `${total ? (done / total) * 100 : 0}%` }} /></div>
          </div>

          <div className="grid g6">
            {DECISIONS.map((d) => <Kpi key={d} label={DECISION_META[d].label} value={live.find((x) => x.name === d).value} />)}
            <Kpi label="Avg processing" value={ms(avgProc, 0)} sub="decode + model + Grad-CAM + store" />
            <Kpi label="Failed files" value={errors.length} />
            {agree !== null && <Kpi label="Label agreement" value={pct(agree)} sub={`n=${labelled.length}, simulation only`} />}
          </div>

          <div className="grid g3" style={{ alignItems: "start" }}>
            <div className="card span2">
              <h2>Inspection sequence</h2>
              <div className="table-wrap" style={{ maxHeight: 520, overflowY: "auto" }}>
                <table>
                  <thead><tr><th className="num">#</th><th></th><th>Product</th><th>Predicted defect</th><th className="num">Conf.</th><th>Decision</th><th className="num">Processing</th><th className="num">Model</th>{labelled.length > 0 && <th>Label</th>}</tr></thead>
                  <tbody>
                    {events.map((e, i) => (
                      <tr key={e.inspection_id} className={i === 0 && running ? "flash" : ""}>
                        <td className="num">{e.sequence_no}</td>
                        <td><img className="thumb" src={e.gradcam_url} alt="" /></td>
                        <td className="mono small ellipsis" title={e.product_id}>…{e.product_id.slice(-9)}</td>
                        <td><ClassLabel name={e.predicted_class} /></td>
                        <td className="num">{pct(e.confidence)}</td>
                        <td><DecisionBadge decision={e.decision} /></td>
                        <td className="num">{ms(e.processing_ms, 0)}</td>
                        <td className="num">{ms(e.model_latency_ms, 1)}</td>
                        {labelled.length > 0 && (
                          <td style={{ color: e.ground_truth === e.predicted_class ? "var(--pass)" : "var(--reject)" }}>{pretty(e.ground_truth)}</td>
                        )}
                      </tr>
                    ))}
                    {errors.map((e) => (
                      <tr key={`err${e.sequence_no}`}><td className="num">{e.sequence_no}</td><td colSpan={8} className="error">{e.source_reference}: {e.error}</td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
            <div className="grid" style={{ gap: 16 }}>
              {latest && (
                <div className="card tight">
                  <h2>Current item #{latest.sequence_no}</h2>
                  <div className="img-box"><img src={latest.gradcam_url} alt="Grad-CAM of latest item" /></div>
                  <div style={{ marginTop: 8 }}><ClassLabel name={latest.predicted_class} /> · {pct(latest.confidence)}</div>
                  <div style={{ marginTop: 6 }}><DecisionBadge decision={latest.decision} /></div>
                  <div className="small muted" style={{ marginTop: 6 }}>Grad-CAM is an explanation of model behaviour, not a verified defect boundary.</div>
                </div>
              )}
              <div className="card tight">
                <h2>Decisions so far</h2>
                <ResponsiveContainer width="100%" height={170}>
                  <BarChart data={live}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="name" tickFormatter={(v) => DECISION_META[v].short} />
                    <YAxis allowDecimals={false} />
                    <Tooltip labelFormatter={(v) => DECISION_META[v].label} />
                    <Bar dataKey="value">{live.map((d) => <Cell key={d.name} fill={DECISION_HEX[d.name]} />)}</Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {summary && <BatchSummary s={summary} />}
        </div>
      )}
    </>
  );
}

function BatchSummary({ s }) {
  return (
    <div className="card">
      <h2>Batch summary (from server)</h2>
      <div className="grid g4">
        <Kpi label="Inspected" value={`${s.n_inspected}/${s.n_items}`} sub={`failed ${s.n_failed}`} />
        <Kpi label="Wall time" value={s.wall_seconds ? `${s.wall_seconds}s` : "—"} sub="includes pacing pauses" />
        <Kpi label="Median processing" value={ms(s.processing_ms?.median, 0)} sub={`max ${ms(s.processing_ms?.max, 0)}`} />
        <Kpi label="Median model latency" value={ms(s.model_latency_ms?.median, 1)} />
      </div>
      <div className="grid g3" style={{ marginTop: 12 }}>
        <div><h3>Decisions</h3>{Object.entries(s.decision_counts).map(([k, v]) => <div key={k} className="small"><DecisionBadge decision={k} /> {v}</div>)}</div>
        <div><h3>Predicted defects</h3>{Object.entries(s.defect_counts).map(([k, v]) => <div key={k} className="small"><ClassLabel name={k} /> · {v}</div>)}</div>
        <div><h3>Review queue</h3>{Object.entries(s.review_status_counts).map(([k, v]) => <div key={k} className="small">{pretty(k)}: {v}</div>)}
          {s.ground_truth_agreement && <div className="small" style={{ marginTop: 8 }}>Agreement with dataset labels: <b>{pct(s.ground_truth_agreement.accuracy)}</b> (n={s.ground_truth_agreement.n})</div>}
        </div>
      </div>
      <div className="small muted" style={{ marginTop: 10 }}>{s.notice}</div>
    </div>
  );
}
