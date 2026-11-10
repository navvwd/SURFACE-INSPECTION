import { Activity, BarChart3, Boxes, Flame, ScanSearch } from "lucide-react";
import { CLASS_LABEL } from "./useSiteData.js";
import { fmtInt } from "./primitives.jsx";

const CLASS_HEX = { Crazing: "#16A9F5", Inclusion: "#F59E0B", Patches: "#8B5CF6", Pitted_Surface: "#10B981", "Rolled-in_Scale": "#F43F5E", Scratches: "#087FC4" };

function Shell({ icon: Icon, title, pill, children, className = "" }) {
  return (
    <div className={`glass-white rounded-[22px] p-3.5 text-brand-ink shadow-float ring-1 ring-white/70 ${className}`}>
      <div className="mb-2.5 flex items-center gap-2">
        <span className="grid h-7 w-7 place-items-center rounded-lg bg-brand/10 text-brand"><Icon className="h-4 w-4" /></span>
        <span className="whitespace-nowrap font-display text-[13px] font-semibold">{title}</span>
        <span className="ml-auto">{pill}</span>
      </div>
      {children}
    </div>
  );
}

export function Pill({ live, children }) {
  return (
    <span className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider ${
      live ? "bg-lime/60 text-brand-ink" : "bg-brand-ink/5 text-brand-ink/60"}`}>
      {live && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-brand-ink" />}
      {children}
    </span>
  );
}

/* Card 1 - Surface inspection (real model output on a held-out test image) */
export function SurfaceCard({ brand }) {
  const ex = brand?.examples?.Scratches;
  return (
    <Shell icon={ScanSearch} title="Surface Inspection" pill={<Pill>Example</Pill>}>
      <div className="relative overflow-hidden rounded-xl bg-black">
        <img src="/brand/sc.jpg" alt="Steel surface with a scratch (NEU-CLS test image)" className="aspect-[4/3] w-full object-cover opacity-95" />
        <div className="pointer-events-none absolute inset-x-0 top-0 h-1/4 animate-scan bg-gradient-to-b from-transparent via-lime/40 to-transparent" />
        <span className="absolute left-2 top-2 rounded-md bg-black/55 px-1.5 py-0.5 font-mono text-[10px] text-white/90">200×200 · gray</span>
      </div>
      <div className="mt-2.5 flex items-end justify-between">
        <div>
          <div className="text-[11px] text-brand-ink/55">Predicted defect</div>
          <div className="font-display text-[15px] font-semibold">Scratch detected</div>
        </div>
        <div className="text-right">
          <div className="text-[11px] text-brand-ink/55">Confidence</div>
          <div className="font-mono text-[15px] font-semibold text-brand">{ex ? `${(ex.confidence * 100).toFixed(1)}%` : "—"}</div>
        </div>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-brand/10">
        <div className="h-full rounded-full bg-gradient-to-r from-brand to-brand-electric" style={{ width: ex ? `${ex.confidence * 100}%` : "0%" }} />
      </div>
    </Shell>
  );
}

/* Card 2 - defect classification */
export function ClassificationCard({ brand }) {
  const ex = brand?.examples?.Inclusion;
  const rows = ["Crazing", "Inclusion", "Patches", "Scratches"];
  return (
    <Shell icon={Boxes} title="Defect Classification" pill={<Pill>6 classes</Pill>}>
      <ul className="space-y-1.5">
        {rows.map((c) => {
          const p = ex?.probabilities?.[c] ?? 0;
          const on = ex?.predicted_class === c;
          return (
            <li key={c} className={`flex items-center gap-2 rounded-lg px-2 py-1.5 text-[12.5px] ${on ? "bg-brand/10 ring-1 ring-brand/20" : ""}`}>
              <span className="h-2 w-2 rounded-sm" style={{ background: CLASS_HEX[c] }} />
              <span className={on ? "font-semibold" : "text-brand-ink/70"}>{CLASS_LABEL[c]}</span>
              <span className="ml-auto font-mono text-[11px] text-brand-ink/60">{(p * 100).toFixed(p > 0.01 ? 1 : 2)}%</span>
            </li>
          );
        })}
      </ul>
      <div className="mt-2 text-[10px] leading-snug text-brand-ink/45">Real softmax output · held-out test image</div>
    </Shell>
  );
}

/* Card 3 - Quality analytics (LIVE from the API) */
export function AnalyticsCard({ overview, live }) {
  const dc = overview?.decision_counts || {};
  const total = overview?.totals?.inspections;
  const parts = [["PASS_CANDIDATE", "Pass", "#22C55E"], ["MANUAL_REVIEW", "Review", "#F59E0B"], ["REJECT_CANDIDATE", "Reject", "#EF4444"]];
  const sum = parts.reduce((a, [k]) => a + (dc[k] || 0), 0);
  const defects = Object.entries(overview?.defect_counts || {});
  const maxD = Math.max(1, ...defects.map(([, v]) => v));
  return (
    <Shell icon={BarChart3} title="Quality Analytics" pill={<Pill live={live}>{live ? "Live" : "Demo preview"}</Pill>}>
      <div className="flex items-baseline gap-2">
        <span className="font-display text-3xl font-semibold tracking-tight">{fmtInt(total)}</span>
        <span className="text-[11px] text-brand-ink/55">inspections recorded</span>
      </div>
      <div className="mt-2.5 flex h-2 overflow-hidden rounded-full bg-brand-ink/5">
        {sum > 0 && parts.map(([k, , c]) => <div key={k} style={{ width: `${((dc[k] || 0) / sum) * 100}%`, background: c }} />)}
      </div>
      <div className="mt-1.5 flex justify-between text-[10.5px] text-brand-ink/65">
        {parts.map(([k, l, c]) => (
          <span key={k} className="inline-flex items-center gap-1"><span className="h-1.5 w-1.5 rounded-full" style={{ background: c }} />{l} {fmtInt(dc[k] ?? (live ? 0 : null))}</span>
        ))}
      </div>
      <div className="mt-3 flex h-12 items-end gap-1.5">
        {(defects.length ? defects : Object.keys(CLASS_HEX).map((k) => [k, 0])).map(([k, v]) => (
          <div key={k} className="flex-1 rounded-t-[4px]" title={`${CLASS_LABEL[k]}: ${v}`}
               style={{ height: `${Math.max(6, (v / maxD) * 100)}%`, background: CLASS_HEX[k], opacity: v ? 0.9 : 0.2 }} />
        ))}
      </div>
      <div className="mt-1 text-[10px] text-brand-ink/45">{live ? "Defect distribution · from the inspection database" : "Start the API to show live inspection data"}</div>
    </Shell>
  );
}

/* Card 4 - Grad-CAM */
export function GradCamCard({ code = "in" }) {
  return (
    <Shell icon={Flame} title="Grad-CAM Visualization" pill={<Pill>XAI</Pill>}>
      <div className="grid grid-cols-2 gap-1.5">
        <figure>
          <img src={`/brand/${code}.jpg`} alt="Original steel surface" className="aspect-square w-full rounded-lg object-cover" />
          <figcaption className="mt-1 text-[10px] text-brand-ink/55">Original surface</figcaption>
        </figure>
        <figure>
          <img src={`/brand/${code}_cam.jpg`} alt="Grad-CAM attention heatmap from the trained model" className="aspect-square w-full rounded-lg object-cover" />
          <figcaption className="mt-1 text-[10px] text-brand-ink/55">Model attention map</figcaption>
        </figure>
      </div>
      <div className="mt-2 text-[10px] leading-snug text-brand-ink/45">Explains model behaviour, not a measured defect boundary.</div>
    </Shell>
  );
}

/* Card 5 - Batch monitoring (LIVE latest batch) */
export function BatchCard({ batch, live }) {
  const s = batch?.summary;
  const status = batch?.status;
  const tone = status === "completed" ? "bg-emerald-500/15 text-emerald-700" : status === "running" ? "bg-brand/15 text-brand" : "bg-brand-ink/5 text-brand-ink/60";
  return (
    <Shell icon={Activity} title="Batch Monitoring" pill={<Pill live={live && !!batch}>{live && batch ? "Live" : "Demo preview"}</Pill>}>
      {batch ? (
        <>
          <div className="flex items-center justify-between gap-2">
            <span className="truncate font-mono text-[11.5px] text-brand-ink/80">{batch.batch_id}</span>
            <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase ${tone}`}>{status}</span>
          </div>
          <div className="mt-2.5 grid grid-cols-3 gap-2 text-center">
            <Stat label="Inspected" value={`${s?.n_inspected ?? 0}/${s?.n_items ?? 0}`} />
            <Stat label="Median time" value={s?.processing_ms ? `${Math.round(s.processing_ms.median)} ms` : "—"} />
            <Stat label="To review" value={fmtInt(s?.decision_counts?.MANUAL_REVIEW ?? 0)} />
          </div>
          <div className="mt-2.5 h-1.5 overflow-hidden rounded-full bg-brand/10">
            <div className="h-full rounded-full bg-lime" style={{ width: `${s?.n_items ? (s.n_inspected / s.n_items) * 100 : 0}%` }} />
          </div>
        </>
      ) : (
        <div className="text-[12px] text-brand-ink/60">No batch has been run yet. Start a simulated line in the console.</div>
      )}
    </Shell>
  );
}

function Stat({ label, value }) {
  return (
    <div className="rounded-xl bg-brand/5 px-1.5 py-2">
      <div className="font-display text-[14px] font-semibold">{value}</div>
      <div className="text-[9.5px] uppercase tracking-wider text-brand-ink/50">{label}</div>
    </div>
  );
}
