import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api.js";
import { ErrorMsg, Kpi, Loading, useApi } from "../components/ui.jsx";
import { CLASSES, ms, pct, pretty } from "../constants.js";

const C1 = "#4e9fd1", C2 = "#e0803a", C3 = "#3fb27f";

export default function ModelPerformance() {
  const models = useApi(() => api.models());
  const comp = useApi(() => api.comparison());
  const policy = useApi(() => api.policy());
  const [key, setKey] = useState(null);
  useEffect(() => { if (!key && models.data?.length) setKey(models.data[0].key); }, [models.data, key]);

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Model Performance</h1>
          <p>Every number on this page is read from artefacts written by the training and evaluation scripts (<code>models/*/evaluation.json</code>, <code>reports/</code>). Test split: 270 held-out images, used only once for final evaluation.</p>
        </div>
      </div>
      <div className="notice warn" style={{ marginBottom: 16 }}>
        <strong>Academic benchmark vs factory deployment.</strong> These metrics describe NEU-CLS: 1,800 images from one acquisition
        setup, six defect types and no defect-free surfaces. A production line brings different cameras, lighting, steel grades and unseen
        defect types, so these figures are an upper bound for that setting, not an estimate. Re-validation on plant data would be mandatory.
      </div>

      {comp.loading ? <Loading /> : comp.error ? <ErrorMsg error={comp.error} /> : <Comparison c={comp.data} />}

      <div className="card" style={{ marginTop: 16 }}>
        <div className="row" style={{ alignItems: "center", marginBottom: 12 }}>
          <h2 style={{ margin: 0 }}>Model detail</h2><span className="spacer" />
          <div className="tabs">
            {(models.data || []).map((m) => (
              <button key={m.key} className={key === m.key ? "on" : ""} onClick={() => setKey(m.key)}>{m.key}</button>
            ))}
          </div>
        </div>
        {key && <ModelDetail k={key} />}
      </div>

      {policy.data && (
        <div className="card" style={{ marginTop: 16 }}>
          <h2>Active decision policy v{policy.data.version}</h2>
          <div className="grid g2">
            <table>
              <thead><tr><th>Predicted class</th><th>Configured action</th></tr></thead>
              <tbody>{Object.entries(policy.data.class_actions).map(([c, a]) => <tr key={c}><td>{pretty(c)}</td><td><code>{a}</code></td></tr>)}</tbody>
            </table>
            <div className="small">
              <div>Manual review if confidence &lt; <b>{policy.data.min_confidence}</b>, top-1/top-2 margin &lt; <b>{policy.data.min_margin}</b>,
                normalised entropy &gt; <b>{policy.data.max_normalized_entropy}</b>, or the input deviates from the training contract.</div>
              <div style={{ marginTop: 6 }}>Automatic <b>reject candidate</b> additionally needs confidence ≥ <b>{policy.data.reject_min_confidence}</b>.
                Confidence alone never rejects; the class must also be configured as a reject class.</div>
              <div className="muted" style={{ marginTop: 6 }}>Class actions are an illustrative default, not a metallurgical specification.</div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function Comparison({ c }) {
  if (!c.comparison) return <div className="card muted">Comparison not generated yet (run <code>training.compare_models</code>).</div>;
  const rows = c.comparison.models;
  const mc = c.comparison.mcnemar_exact;
  const sb = c.shortcut_baseline?.baselines;
  const f1Data = CLASSES.map((cl) => ({ name: cl, ...Object.fromEntries(rows.map((r) => [r.model, r.per_class_f1[cl]])) }));
  return (
    <div className="grid g3" style={{ alignItems: "start" }}>
      <div className="card span2">
        <h2>Custom CNN vs ResNet18 (test split, n={c.comparison.test_split_n})</h2>
        <div className="table-wrap">
          <table>
            <thead><tr><th>Metric</th>{rows.map((r) => <th key={r.model} className="num">{r.model}</th>)}</tr></thead>
            <tbody>
              <Tr label="Test accuracy [95% CI]" rows={rows} f={(r) => `${pct(r.test_accuracy, 2)} [${pct(r.test_acc_ci95[0])}–${pct(r.test_acc_ci95[1])}]`} />
              <Tr label="Macro-F1 [95% CI]" rows={rows} f={(r) => `${r.test_macro_f1.toFixed(4)} [${r.test_macro_f1_ci95[0].toFixed(3)}–${r.test_macro_f1_ci95[1].toFixed(3)}]`} />
              <Tr label="Test errors (of 270)" rows={rows} f={(r) => r.test_errors} />
              <Tr label="Validation accuracy" rows={rows} f={(r) => pct(r.val_accuracy, 2)} />
              <Tr label="Parameters" rows={rows} f={(r) => r.params.toLocaleString()} />
              <Tr label="Model file (incl. optimizer state)" rows={rows} f={(r) => `${r.file_mb} MB`} />
              <Tr label="Training time (shared CPU*)" rows={rows} f={(r) => `${r.train_minutes} min`} />
              <Tr label="Latency batch=1 median / p95" rows={rows} f={(r) => `${r.latency_b1_median_ms.toFixed(1)} / ${r.latency_b1_p95_ms.toFixed(1)} ms`} />
              <Tr label="Throughput batch=32" rows={rows} f={(r) => `${r.throughput_b32_img_s.toFixed(0)} img/s`} />
              {rows[0].decision_test && <>
                <Tr label="Policy automation rate" rows={rows} f={(r) => pct(r.decision_test.automation_rate)} />
                <Tr label="Accuracy of auto-decided" rows={rows} f={(r) => pct(r.decision_test.auto_decided_classification_accuracy, 2)} />
                <Tr label="Escaped reject-class defects" rows={rows} f={(r) => r.decision_test.escaped_reject_class_defects} />
                <Tr label="False rejects" rows={rows} f={(r) => r.decision_test.false_rejects} />
              </>}
            </tbody>
          </table>
        </div>
        <div className="small muted" style={{ marginTop: 8 }}>
          * Training times were measured on a laptop CPU shared with other jobs and with different epoch counts (early stopping);
          they are indicative only. Latency and throughput were measured in isolation after warm-up.
        </div>
        {mc && (
          <div className="small" style={{ marginTop: 10 }}>
            <b>McNemar exact test</b> on paired test predictions: only {rows[0].model} correct = {mc.only_first_correct}, only {rows[1].model} correct = {mc.only_second_correct},
            p = {mc.exact_p_value.toFixed(4)} → the accuracy difference is <b>{mc.significant_at_0_05 ? "statistically significant" : "not statistically significant"}</b> at α = 0.05.
          </div>
        )}
      </div>
      <div className="grid" style={{ gap: 16 }}>
        <div className="card">
          <h2>Per-class F1 (test)</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={f1Data}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="name" tickFormatter={(v) => pretty(v).split(" ")[0]} tick={{ fontSize: 10 }} interval={0} />
              <YAxis domain={[0.8, 1]} />
              <Tooltip labelFormatter={pretty} formatter={(v) => v.toFixed(3)} />
              <Legend />
              {rows.map((r, i) => <Bar key={r.model} dataKey={r.model} fill={[C1, C2, C3][i]} />)}
            </BarChart>
          </ResponsiveContainer>
        </div>
        {sb && (
          <div className="card">
            <h2>Shortcut baseline</h2>
            <div className="small">
              A logistic regression that sees only each image's <b>mean and std of brightness</b> reaches{" "}
              <b>{pct(sb.mean_std.test_accuracy)}</b> test accuracy (32-bin histogram: {pct(sb.histogram32.test_accuracy)}; chance {pct(c.shortcut_baseline.chance_accuracy)}).
              NEU-CLS classes differ in global exposure, so part of the task can be solved without looking at defect structure.
              The lighting-robustness curves below show how much each CNN depends on that.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const Tr = ({ label, rows, f }) => (
  <tr><td>{label}</td>{rows.map((r) => <td key={r.model} className="num">{f(r)}</td>)}</tr>
);

function ModelDetail({ k }) {
  const [name, version] = k.split(":");
  const { data, error, loading } = useApi(() => api.model(name, version), [k]);
  if (loading) return <Loading />;
  if (error) return <ErrorMsg error={error} />;
  const ev = data.evaluation;
  if (!ev) return <div className="muted">This model has not been evaluated yet.</div>;
  const t = ev.test, v = ev.validation;
  const perClass = CLASSES.map((c) => ({ name: c, ...t.per_class[c] }));
  const rob = (kind) => ev.robustness_test.filter((r) => r.perturbation === kind);
  const da = data.decision_analysis?.test;
  const san = data.gradcam_sanity;

  return (
    <div className="grid" style={{ gap: 16 }}>
      <div className="grid g6">
        <Kpi accent label="Test accuracy" value={pct(t.accuracy, 2)} sub={`95% CI ${pct(t.accuracy_ci95_wilson[0])}–${pct(t.accuracy_ci95_wilson[1])}`} />
        <Kpi label="Macro-F1" value={t.macro_f1.toFixed(4)} sub={`P ${t.macro_precision.toFixed(3)} · R ${t.macro_recall.toFixed(3)}`} />
        <Kpi label="Validation acc." value={pct(v.accuracy, 2)} sub={`macro-F1 ${v.macro_f1.toFixed(4)}`} />
        <Kpi label="Test errors" value={`${t.n - t.correct}/${t.n}`} />
        <Kpi label="Latency (b=1)" value={ms(ev.latency_cpu.batch_1.median_ms)} sub={`p95 ${ms(ev.latency_cpu.batch_1.p95_ms)} · CPU`} />
        <Kpi label="Parameters" value={(ev.total_params / 1e6).toFixed(2) + "M"} sub={`${ev.model_file_mb} MB file`} />
      </div>

      <div className="grid g2">
        <div className="card tight">
          <h2>Training & validation loss</h2>
          <ResponsiveContainer width="100%" height={230}>
            <LineChart data={data.history}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="epoch" />
              <YAxis />
              <Tooltip formatter={(v) => v.toFixed(4)} />
              <Legend />
              <Line dataKey="loss" name="train" stroke={C1} dot={false} strokeWidth={2} />
              <Line dataKey="val_loss" name="validation" stroke={C2} dot={false} strokeWidth={2} />
              {stageStarts(data.history).map((s) => <ReferenceLine key={s.epoch} x={s.epoch} stroke="#888" strokeDasharray="4 4" label={{ value: s.stage, fontSize: 10, position: "insideTopRight" }} />)}
            </LineChart>
          </ResponsiveContainer>
        </div>
        <div className="card tight">
          <h2>Training & validation accuracy</h2>
          <ResponsiveContainer width="100%" height={230}>
            <LineChart data={data.history}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="epoch" />
              <YAxis domain={[0, 1]} />
              <Tooltip formatter={(v) => pct(v, 2)} />
              <Legend />
              <Line dataKey="accuracy" name="train (augmented)" stroke={C1} dot={false} strokeWidth={2} />
              <Line dataKey="val_accuracy" name="validation" stroke={C2} dot={false} strokeWidth={2} />
              {stageStarts(data.history).map((s) => <ReferenceLine key={s.epoch} x={s.epoch} stroke="#888" strokeDasharray="4 4" />)}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid g2">
        <div className="card tight">
          <h2>Per-class precision / recall / F1 (test)</h2>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={perClass}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis dataKey="name" tickFormatter={(v) => pretty(v).split(" ")[0]} tick={{ fontSize: 10 }} interval={0} />
              <YAxis domain={[0.7, 1]} />
              <Tooltip labelFormatter={pretty} formatter={(v) => v.toFixed(3)} />
              <Legend />
              <Bar dataKey="precision" fill={C1} /><Bar dataKey="recall" fill={C3} /><Bar dataKey="f1" fill={C2} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="card tight">
          <h2>Confusion matrix (test, rows = true class)</h2>
          <ConfusionMatrix cm={t.confusion_matrix} />
        </div>
      </div>

      <div className="grid g2">
        <div className="card tight">
          <h2>Robustness to lighting changes (test)</h2>
          <div className="grid g2">
            <MiniLine data={rob("brightness_shift")} x="value" label="added gray levels" />
            <MiniLine data={rob("contrast_scale")} x="value" label="contrast factor" />
          </div>
          <div className="small muted">Synthetic global brightness/contrast changes. Training augmentation covered ±38 gray levels and ×0.7–1.3 contrast; values outside that range probe extrapolation.</div>
        </div>
        <div className="card tight">
          <h2>Decision engine on test split</h2>
          {da ? (
            <table>
              <tbody>
                <tr><td>Pass / Reject / Review</td><td className="num">{da.decision_counts.PASS_CANDIDATE} / {da.decision_counts.REJECT_CANDIDATE} / {da.decision_counts.MANUAL_REVIEW}</td></tr>
                <tr><td>Automation rate (not sent to review)</td><td className="num">{pct(da.automation_rate)}</td></tr>
                <tr><td>Classification accuracy of auto-decided items</td><td className="num">{pct(da.auto_decided_classification_accuracy, 2)}</td></tr>
                <tr><td>Misclassifications caught by review gates</td><td className="num">{da.misclassifications_caught_by_review} of {da.misclassifications_total}</td></tr>
                <tr><td>Escaped reject-class defects (critical)</td><td className="num">{da.escaped_reject_class_defects}</td></tr>
                <tr><td>False rejects</td><td className="num">{da.false_rejects}</td></tr>
              </tbody>
            </table>
          ) : <div className="muted">Not analysed.</div>}
          {san && (
            <div className="small" style={{ marginTop: 12 }}>
              <b>Grad-CAM sanity check</b> (n={san.n_images}): Spearman ρ between maps of the trained model and the same architecture with random weights
              = {san.trained_vs_random_weights_spearman_mean.toFixed(3)} (|ρ| {san.trained_vs_random_weights_spearman_abs_mean.toFixed(3)}); flip-consistency ρ = {san.flip_consistency_spearman_mean.toFixed(3)}.
              <div className="muted">{san.interpretation}</div>
            </div>
          )}
        </div>
      </div>

      {data.figures.gradcam_examples && (
        <div className="card tight">
          <h2>Grad-CAM on held-out test images</h2>
          <img src={data.figures.gradcam_examples} alt="Grad-CAM examples" style={{ width: "100%", borderRadius: 6, background: "#fff" }} />
        </div>
      )}
      <div className="small muted">
        Training: {(ev.training.total_training_seconds / 60).toFixed(1)} min on CPU · {ev.training.stages.map((s) => `${s.name}: ${s.epochs_run} epochs (best ${s.best_epoch})`).join(" · ")} · evaluated {ev.evaluated_at} · {ev.latency_hardware.processor}
      </div>
    </div>
  );
}

function stageStarts(history) {
  const out = [];
  history.forEach((h, i) => { if (i > 0 && h.stage !== history[i - 1].stage) out.push({ epoch: h.epoch, stage: h.stage }); });
  return out;
}

function MiniLine({ data, x, label }) {
  return (
    <ResponsiveContainer width="100%" height={170}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey={x} tick={{ fontSize: 10 }} label={{ value: label, position: "insideBottom", offset: -2, fontSize: 10 }} />
        <YAxis domain={[0, 1]} tickFormatter={(v) => `${Math.round(v * 100)}%`} />
        <Tooltip formatter={(v) => pct(v)} />
        <Line dataKey="accuracy" stroke={C1} strokeWidth={2} />
      </LineChart>
    </ResponsiveContainer>
  );
}

function ConfusionMatrix({ cm }) {
  return (
    <div className="table-wrap">
      <table className="cm">
        <thead>
          <tr><th></th>{CLASSES.map((c) => <th key={c} className="rot">{pretty(c)}</th>)}</tr>
        </thead>
        <tbody>
          {cm.map((row, i) => {
            const total = row.reduce((a, b) => a + b, 0);
            return (
              <tr key={i}>
                <th style={{ textAlign: "right", paddingRight: 6 }}>{pretty(CLASSES[i])}</th>
                {row.map((v, j) => {
                  const f = total ? v / total : 0;
                  const bg = i === j ? `rgba(63,178,127,${0.15 + f * 0.85})` : v ? `rgba(229,83,75,${0.25 + f * 2})` : "var(--panel-2)";
                  return <td key={j} style={{ background: bg, color: f > 0.5 ? "#fff" : "var(--text)" }} title={`true ${CLASSES[i]} → predicted ${CLASSES[j]}`}>{v}</td>;
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
