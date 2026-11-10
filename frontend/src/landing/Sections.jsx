import { motion, useReducedMotion } from "framer-motion";
import {
  Activity, ArrowUpRight, BarChart3, Camera, Car, CircleCheck, Cpu, Factory, FileText, Flame,
  Layers, Microscope, ScanSearch, ShieldCheck, SlidersHorizontal, Wrench,
} from "lucide-react";
import { Link } from "react-router-dom";
import { Eyebrow, LimeButton, Reveal, fmtInt } from "./primitives.jsx";
import { CLASS_LABEL } from "./useSiteData.js";
import { BRAND } from "../brand.js";

/* ───────────────────────── 5. Trust / technology strip ───────────────────────── */
const TECH = ["Computer Vision", "Deep Learning", "Grad-CAM Explainability", "Surface Analytics", "Inspection Management"];

export function TrustStrip() {
  const items = [...TECH, ...TECH, ...TECH, ...TECH];
  return (
    <section className="relative bg-white py-14">
      <Reveal className="mx-auto max-w-3xl px-6 text-center">
        <p className="font-display text-lg font-medium text-brand-ink/70 sm:text-xl">
          Built for the next generation of industrial quality inspection.
        </p>
      </Reveal>
      <div className="mask-fade-x mt-9 overflow-hidden">
        <div className="flex w-max animate-marquee gap-4">
          {items.map((t, i) => (
            <span key={i} className="inline-flex items-center gap-3 whitespace-nowrap rounded-full border border-brand-ink/10 bg-brand-soft px-6 py-3 font-display text-[15px] font-medium text-brand-ink/75">
              <span className="h-1.5 w-1.5 rounded-full bg-brand" />{t}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ───────────────────────── 6. About (bento) ───────────────────────── */
export function About({ data }) {
  const { overview, live, brand } = data;
  return (
    <section id="platform" className="scroll-mt-24 bg-white px-5 py-24 sm:py-32">
      <div className="mx-auto max-w-6xl">
        <Reveal><Eyebrow>About {BRAND.name}</Eyebrow></Reveal>
        <div className="mt-6 grid gap-10 lg:grid-cols-[1.4fr_1fr] lg:items-end">
          <Reveal as="h2" delay={0.05} className="font-display text-4xl font-semibold leading-[1.02] tracking-[-0.035em] text-brand-ink sm:text-6xl">
            Manufacturing deserves a <span className="text-brand">smarter way</span> to see{" "}
            <span className="relative inline-block">
              <span className="relative z-10">quality.</span>
              <span aria-hidden className="absolute inset-x-[-4px] bottom-1 z-0 h-[38%] rounded-md bg-lime" />
            </span>
          </Reveal>
          <Reveal delay={0.12} className="text-lg leading-relaxed text-brand-ink/65">
            {BRAND.description} Under the hood, computer vision and deep learning analyse each surface image and classify the
            defect category.
          </Reveal>
        </div>

        <div className="mt-16 grid auto-rows-[minmax(220px,auto)] gap-4 md:grid-cols-6">
          {/* 1 - large image card */}
          <BentoCard className="md:col-span-4 md:row-span-2" delay={0} n="01" icon={ScanSearch} title="Intelligent Inspection"
                     text="Automated surface defect classification across six steel defect types, with a confidence score and decision for every image.">
            <div className="mt-6 grid grid-cols-3 gap-2 sm:grid-cols-6">
              {Object.entries(brand?.examples || {}).map(([cls, ex]) => (
                <figure key={cls} className="group/img relative overflow-hidden rounded-2xl">
                  <img src={`/brand/${ex.code}.jpg`} alt={`${CLASS_LABEL[cls]} sample`} className="aspect-[3/4] w-full object-cover transition-transform duration-700 group-hover/img:scale-110" />
                  <figcaption className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/75 to-transparent px-2 pb-2 pt-6 text-[10.5px] font-medium text-white">{CLASS_LABEL[cls]}</figcaption>
                </figure>
              ))}
            </div>
            <p className="mt-3 text-xs text-brand-ink/45">Samples from the NEU-CLS steel surface dataset (200×200 grayscale).</p>
          </BentoCard>

          {/* 2 - Grad-CAM */}
          <BentoCard className="md:col-span-2 md:row-span-2" delay={0.08} n="02" icon={Flame} title="Explainable Results"
                     text="Visualize model attention using Grad-CAM, so inspectors can see which regions drove each prediction." dark>
            <div className="relative mt-6 overflow-hidden rounded-2xl">
              <img src="/brand/sc.jpg" alt="Steel surface" className="aspect-square w-full object-cover" />
              <motion.img src="/brand/sc_cam.jpg" alt="Grad-CAM heatmap" className="absolute inset-0 aspect-square w-full object-cover"
                          initial={{ clipPath: "inset(0 100% 0 0)" }} whileInView={{ clipPath: "inset(0 0% 0 0)" }}
                          viewport={{ once: false, margin: "-120px" }} transition={{ duration: 1.6, ease: [0.65, 0, 0.35, 1] }} />
            </div>
            <p className="mt-3 text-xs text-white/55">Heatmaps explain model behaviour; they are not verified defect boundaries.</p>
          </BentoCard>

          {/* 3 - Quality intelligence (live numbers) */}
          <BentoCard className="md:col-span-3" delay={0.1} n="03" icon={BarChart3} title="Quality Intelligence"
                     text="Understand inspection trends and defect patterns across every image processed.">
            <div className="mt-5 flex flex-wrap items-end gap-8">
              <BigNumber value={fmtInt(overview?.totals?.inspections)} label={live ? "inspections in the database" : "start the API for live data"} />
              <BigNumber value={fmtInt(overview?.totals?.pending_review)} label="awaiting human review" />
            </div>
          </BentoCard>

          {/* 4 - Batch monitoring */}
          <BentoCard className="md:col-span-3" delay={0.14} n="04" icon={Activity} title="Batch Monitoring"
                     text="Track inspection outcomes across production batches, image by image, with a batch-level summary.">
            <div className="mt-5 flex flex-wrap items-end gap-8">
              <BigNumber value={fmtInt(overview?.totals?.batches)} label={live ? "batches recorded" : "start the API for live data"} />
              <Link to="/app/batch" className="group mb-1 inline-flex items-center gap-1 text-sm font-semibold text-brand">
                Run a simulated line <ArrowUpRight className="h-4 w-4 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
              </Link>
            </div>
          </BentoCard>
        </div>
      </div>
    </section>
  );
}

function BigNumber({ value, label }) {
  return (
    <div>
      <div className="font-display text-5xl font-semibold tracking-[-0.04em] text-brand-ink">{value}</div>
      <div className="mt-1 text-xs text-brand-ink/50">{label}</div>
    </div>
  );
}

function BentoCard({ className = "", n, icon: Icon, title, text, children, delay = 0, dark = false }) {
  return (
    <Reveal delay={delay} className={className}>
      <motion.div whileHover={{ y: -4 }} transition={{ type: "spring", stiffness: 300, damping: 24 }}
                  className={`group flex h-full flex-col rounded-4xl p-6 sm:p-7 ${dark
                    ? "bg-gradient-to-br from-brand-deep to-brand-navy text-white"
                    : "border border-brand-ink/[0.07] bg-brand-soft text-brand-ink hover:border-brand/25 hover:bg-white hover:shadow-soft"} transition-colors duration-300`}>
        <div className="flex items-center justify-between">
          <span className={`grid h-11 w-11 place-items-center rounded-2xl ${dark ? "bg-white/10 text-lime" : "bg-white text-brand shadow-soft"}`}><Icon className="h-5 w-5" /></span>
          <span className={`font-display text-sm font-semibold ${dark ? "text-white/40" : "text-brand-ink/25"}`}>{n}</span>
        </div>
        <h3 className="mt-5 font-display text-2xl font-semibold tracking-tight">{title}</h3>
        <p className={`mt-2 max-w-md leading-relaxed ${dark ? "text-white/70" : "text-brand-ink/60"}`}>{text}</p>
        {children}
      </motion.div>
    </Reveal>
  );
}

/* ───────────────────────── 7. How it works ───────────────────────── */
const STEPS = [
  [Camera, "Image Acquisition", "A steel surface image is captured or uploaded and registered with product and batch IDs."],
  [SlidersHorizontal, "Image Preprocessing", "Converted to the 200×200 grayscale input contract; off-contract inputs are flagged for review."],
  [Cpu, "CNN-Based Analysis", "A Custom CNN or fine-tuned ResNet18 extracts surface features; Grad-CAM records where it looked."],
  [Layers, "Defect Classification", "Six defect types - crazing, inclusion, patches, pitted surface, rolled-in scale, scratches."],
  [ShieldCheck, "Inspection Decision", "A configurable policy proposes pass, reject or manual review. A person makes the final call."],
];

export function HowItWorks() {
  const reduce = useReducedMotion();
  return (
    <section className="relative overflow-hidden bg-brand-soft px-5 py-24 sm:py-32">
      <div className="mx-auto max-w-6xl">
        <div className="flex flex-col items-start justify-between gap-6 md:flex-row md:items-end">
          <div>
            <Reveal><Eyebrow>How it works</Eyebrow></Reveal>
            <Reveal as="h2" delay={0.05} className="mt-5 max-w-2xl font-display text-4xl font-semibold leading-[1.03] tracking-[-0.035em] text-brand-ink sm:text-5xl">
              From Surface Image to <span className="text-brand">Quality Intelligence.</span>
            </Reveal>
          </div>
          <Reveal delay={0.1} className="max-w-sm text-brand-ink/60">Five stages, from a raw steel image to a reviewed inspection decision stored with its full audit trail.</Reveal>
        </div>

        <div className="relative mt-16">
          {/* connector line */}
          <div aria-hidden className="absolute left-0 right-0 top-[34px] hidden h-px bg-brand-ink/10 lg:block" />
          <motion.div aria-hidden className="absolute left-0 top-[34px] hidden h-px origin-left bg-gradient-to-r from-brand via-brand-electric to-lime lg:block"
                      style={{ right: 0 }} initial={reduce ? false : { scaleX: 0 }} whileInView={{ scaleX: 1 }}
                      viewport={{ once: true, margin: "-120px" }} transition={{ duration: 1.8, ease: [0.65, 0, 0.35, 1] }} />
          <ol className="grid gap-5 sm:grid-cols-2 lg:grid-cols-5">
            {STEPS.map(([Icon, title, text], i) => (
              <Reveal as="li" key={title} delay={0.15 + i * 0.12} className="relative">
                <div className="relative z-10 grid h-[68px] w-[68px] place-items-center rounded-3xl bg-white text-brand shadow-soft ring-1 ring-brand-ink/5">
                  <Icon className="h-7 w-7" />
                  <span className="absolute -right-2 -top-2 grid h-7 w-7 place-items-center rounded-full bg-brand-ink font-display text-[11px] font-semibold text-lime">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                </div>
                <h3 className="mt-6 font-display text-lg font-semibold text-brand-ink">{title}</h3>
                <p className="mt-2 text-[14.5px] leading-relaxed text-brand-ink/60">{text}</p>
              </Reveal>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}

/* ───────────────────────── 8. Technical architecture (+ research results) ───────────────────────── */
export function Technology({ data }) {
  const { models, live } = data;
  return (
    <section id="technology" className="relative scroll-mt-24 overflow-hidden bg-brand-navy px-5 py-24 text-white sm:py-32">
      <div aria-hidden className="grid-lines absolute inset-0 opacity-40" />
      <div aria-hidden className="absolute -right-40 -top-40 h-[560px] w-[560px] rounded-full bg-[radial-gradient(circle,rgba(22,169,245,0.35),transparent_65%)]" />
      <div className="relative mx-auto max-w-6xl">
        <Reveal><Eyebrow light>Technical architecture</Eyebrow></Reveal>
        <Reveal as="h2" delay={0.05} className="mt-5 max-w-3xl font-display text-4xl font-semibold leading-[1.03] tracking-[-0.035em] sm:text-6xl">
          Engineering beneath <span className="text-lime">every inspection.</span>
        </Reveal>

        <div className="mt-16 grid gap-5 lg:grid-cols-3">
          <TechCard delay={0} icon={Cpu} title="Custom CNN" text="Learns visual surface patterns and classifies steel defects. A compact four-block convolutional network trained from scratch.">
            <NeuralViz />
          </TechCard>
          <TechCard delay={0.1} icon={Layers} title="ResNet18" text="Transfer-learning-based classification and model comparison. ImageNet features, fine-tuned on steel surfaces.">
            <ResidualViz />
          </TechCard>
          <TechCard delay={0.2} icon={Flame} title="Grad-CAM" text="Visual explanation of the image regions influencing predictions, for every inspection the system records.">
            <HeatViz />
          </TechCard>
        </div>

        {/* research: real evaluation numbers from the API, with the benchmark caveat */}
        <div id="research" className="mt-20 scroll-mt-28">
          <Reveal className="rounded-4xl bg-white/[0.06] p-6 ring-1 ring-white/10 sm:p-9">
            <div className="flex flex-col justify-between gap-6 md:flex-row md:items-end">
              <div>
                <div className="inline-flex items-center gap-2 text-sm font-semibold text-lime"><Microscope className="h-4 w-4" /> Research results</div>
                <h3 className="mt-3 max-w-xl font-display text-2xl font-semibold tracking-tight sm:text-3xl">Measured, not promised.</h3>
                <p className="mt-3 max-w-2xl text-white/65">
                  Both models were evaluated on held-out NEU-CLS test images never used for training or tuning. These figures describe an academic
                  benchmark, not performance on a production line, and are not a guarantee of defect detection.
                </p>
              </div>
              <a href="/artifacts/FINAL_REPORT.md" className="inline-flex shrink-0 items-center gap-2 rounded-full px-5 py-3 text-sm font-semibold ring-1 ring-white/25 transition hover:bg-white/10">
                <FileText className="h-4 w-4" /> Technical report
              </a>
            </div>
            <div className="mt-8 grid gap-4 sm:grid-cols-2">
              {live && models?.length ? models.map((m) => (
                <div key={m.key} className="rounded-3xl bg-white/[0.06] p-5 ring-1 ring-white/10">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-sm text-white/70">{m.key}</span>
                    {m.is_default && <span className="rounded-full bg-lime px-2 py-0.5 text-[10px] font-bold uppercase text-brand-ink">Default</span>}
                  </div>
                  <div className="mt-4 grid grid-cols-3 gap-3">
                    <Metric label="Test accuracy" value={m.test_accuracy != null ? `${(m.test_accuracy * 100).toFixed(2)}%` : "—"} />
                    <Metric label="Macro-F1" value={m.test_macro_f1 != null ? m.test_macro_f1.toFixed(3) : "—"} />
                    <Metric label="CPU latency" value={m.latency_b1_median_ms != null ? `${m.latency_b1_median_ms.toFixed(1)} ms` : "—"} />
                  </div>
                </div>
              )) : (
                <div className="rounded-3xl bg-white/[0.06] p-5 text-white/60 ring-1 ring-white/10 sm:col-span-2">
                  Evaluation results are loaded from the running API. Start the backend to show the measured figures here.
                </div>
              )}
            </div>
            <p className="mt-4 text-xs text-white/45">Held-out test split: 270 images (45 per class). Latency: model forward pass on a laptop CPU.</p>
          </Reveal>
        </div>
      </div>
    </section>
  );
}

function Metric({ label, value }) {
  return (
    <div>
      <div className="font-display text-2xl font-semibold tracking-tight">{value}</div>
      <div className="text-[11px] uppercase tracking-wider text-white/45">{label}</div>
    </div>
  );
}

function TechCard({ icon: Icon, title, text, children, delay }) {
  return (
    <Reveal delay={delay}>
      <motion.div whileHover={{ y: -6 }} transition={{ type: "spring", stiffness: 260, damping: 22 }}
                  className="group h-full rounded-4xl bg-gradient-to-b from-white/[0.09] to-white/[0.03] p-6 ring-1 ring-white/10 transition hover:ring-lime/40">
        <div className="h-40 overflow-hidden rounded-3xl bg-brand-navy/60 ring-1 ring-white/10">{children}</div>
        <div className="mt-6 flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-lime text-brand-ink"><Icon className="h-5 w-5" /></span>
          <h3 className="font-display text-2xl font-semibold">{title}</h3>
        </div>
        <p className="mt-3 leading-relaxed text-white/65">{text}</p>
      </motion.div>
    </Reveal>
  );
}

/* animated neural-network layers */
function NeuralViz() {
  const reduce = useReducedMotion();
  const layers = [4, 6, 6, 4, 6];
  const W = 320, H = 160;
  const pts = layers.map((n, i) => Array.from({ length: n }, (_, j) => [30 + (i * (W - 60)) / (layers.length - 1), 20 + ((j + 0.5) * (H - 40)) / n]));
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-full w-full">
      {pts.slice(0, -1).map((col, i) => col.flatMap((a, ai) => pts[i + 1].map((b, bi) => (
        <motion.line key={`${i}-${ai}-${bi}`} x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} stroke="#16A9F5" strokeWidth="0.6"
                     initial={{ opacity: 0.08 }} animate={reduce ? undefined : { opacity: [0.08, 0.5, 0.08] }}
                     transition={{ duration: 2.4, repeat: Infinity, delay: i * 0.35 + ((ai + bi) % 4) * 0.12 }} />
      ))))}
      {pts.flatMap((col, i) => col.map(([x, y], j) => (
        <motion.circle key={`n${i}-${j}`} cx={x} cy={y} r="4" fill={i === pts.length - 1 && j === 2 ? "#D8FF4F" : "#fff"}
                       animate={reduce ? undefined : { scale: [1, 1.35, 1] }} transition={{ duration: 2.4, repeat: Infinity, delay: i * 0.35 }} />
      )))}
    </svg>
  );
}

/* stacked residual blocks with a skip connection */
function ResidualViz() {
  const reduce = useReducedMotion();
  return (
    <svg viewBox="0 0 320 160" className="h-full w-full">
      {[0, 1, 2, 3].map((i) => (
        <motion.g key={i} initial={{ opacity: 0.3 }} animate={reduce ? undefined : { opacity: [0.35, 1, 0.35] }} transition={{ duration: 3, repeat: Infinity, delay: i * 0.4 }}>
          <rect x={28 + i * 70} y={52 - i * 6} width="46" height={56 + i * 12} rx="8" fill="none" stroke="#16A9F5" strokeWidth="1.5" />
          <text x={51 + i * 70} y={86} textAnchor="middle" fill="#fff" fontSize="10" fontFamily="IBM Plex Mono">{["64", "128", "256", "512"][i]}</text>
        </motion.g>
      ))}
      <path d="M51 42 C 90 8, 150 8, 191 30" fill="none" stroke="#D8FF4F" strokeWidth="1.5" strokeDasharray="4 4" />
      <path d="M121 36 C 160 2, 220 2, 261 24" fill="none" stroke="#D8FF4F" strokeOpacity=".6" strokeWidth="1.5" strokeDasharray="4 4" />
      <text x="160" y="150" textAnchor="middle" fill="#ffffff80" fontSize="10" fontFamily="Inter">residual stages · skip connections</text>
    </svg>
  );
}

/* real Grad-CAM heatmap revealed over the real steel image */
function HeatViz() {
  const reduce = useReducedMotion();
  return (
    <div className="relative h-full w-full">
      <img src="/brand/pa.jpg" alt="" className="absolute inset-0 h-full w-full object-cover opacity-80" />
      <motion.img src="/brand/pa_cam.jpg" alt="" className="absolute inset-0 h-full w-full object-cover"
                  animate={reduce ? undefined : { opacity: [0, 0.95, 0.95, 0] }} transition={{ duration: 5, repeat: Infinity, times: [0, 0.3, 0.7, 1] }} />
      <span className="absolute bottom-2 left-2 rounded-md bg-black/55 px-2 py-0.5 text-[10px] text-white/90">Patches · real Grad-CAM output</span>
    </div>
  );
}

/* ───────────────────────── 9. Industrial applications ───────────────────────── */
const APPS = [
  [Factory, "Steel manufacturing", "Classify rolled-in scale, patches and pitted surfaces on hot-rolled strip before coils ship.", "rs"],
  [Wrench, "Metal fabrication", "Catch scratches and handling damage on sheet stock before it is cut, formed or coated.", "sc"],
  [Car, "Automotive components", "Screen surface finish on stamped and pressed parts, where cosmetic defects drive rejects.", "ps"],
  [CircleCheck, "Industrial quality assurance", "Give QA teams an explainable, auditable record of every inspection decision.", "cr"],
];

export function Applications() {
  return (
    <section id="solutions" className="scroll-mt-24 bg-white px-5 py-24 sm:py-32">
      <div className="mx-auto max-w-6xl">
        <div className="flex flex-col justify-between gap-6 md:flex-row md:items-end">
          <div>
            <Reveal><Eyebrow>Solutions</Eyebrow></Reveal>
            <Reveal as="h2" delay={0.05} className="mt-5 max-w-2xl font-display text-4xl font-semibold leading-[1.03] tracking-[-0.035em] text-brand-ink sm:text-5xl">
              Built around real <span className="text-brand">manufacturing challenges.</span>
            </Reveal>
          </div>
          <Reveal delay={0.1} className="max-w-sm text-brand-ink/60">Where automated surface inspection matters most. Imagery shows real steel surface samples.</Reveal>
        </div>
        <div className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {APPS.map(([Icon, title, text, code], i) => (
            <Reveal key={title} delay={i * 0.08} className={i % 2 ? "lg:mt-10" : ""}>
              <motion.article whileHover="hover" className="group relative h-[420px] overflow-hidden rounded-4xl bg-brand-ink">
                <motion.img src={`/brand/${code}.jpg`} alt={`${title}: steel surface sample`} className="absolute inset-0 h-full w-full object-cover opacity-75"
                            variants={{ hover: { scale: 1.08 } }} transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }} />
                <motion.img src={`/brand/${code}_cam.jpg`} alt="" aria-hidden className="absolute inset-0 h-full w-full object-cover"
                            initial={{ opacity: 0 }} variants={{ hover: { opacity: 0.85, scale: 1.08 } }} transition={{ duration: 0.6 }} />
                <div className="absolute inset-0 bg-gradient-to-t from-brand-navy via-brand-navy/40 to-transparent" />
                <div className="absolute inset-x-0 bottom-0 p-6 text-white">
                  <span className="grid h-11 w-11 place-items-center rounded-2xl bg-white/15 backdrop-blur"><Icon className="h-5 w-5" /></span>
                  <h3 className="mt-4 font-display text-xl font-semibold">{title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-white/75">{text}</p>
                </div>
              </motion.article>
            </Reveal>
          ))}
        </div>
        <p className="mt-6 text-xs text-brand-ink/40">Hover a card to reveal the model's Grad-CAM attention for that sample.</p>
      </div>
    </section>
  );
}

/* ───────────────────────── 10. Final CTA ───────────────────────── */
export function FinalCTA() {
  return (
    <section className="bg-white px-4 pb-6 sm:px-6">
      <Reveal className="relative mx-auto max-w-7xl overflow-hidden rounded-[40px] bg-gradient-to-br from-brand-deep via-brand to-brand-electric px-6 py-24 text-center text-white sm:py-32">
        <div aria-hidden className="grid-lines absolute inset-0 opacity-50" />
        <div aria-hidden className="absolute left-1/2 top-0 h-[520px] w-[820px] -translate-x-1/2 rounded-full bg-[radial-gradient(ellipse,rgba(255,255,255,0.35),transparent_60%)]" />
        <div aria-hidden className="absolute inset-x-0 bottom-0 h-40 bg-[url('/brand/strip.jpg')] bg-[length:900px_100%] opacity-20 mix-blend-luminosity" />
        <div className="relative">
          <h2 className="mx-auto max-w-3xl font-display text-4xl font-semibold leading-[1.02] tracking-[-0.04em] sm:text-6xl">
            Make Every Inspection <span className="text-lime">More Precise.</span>
          </h2>
          <p className="mx-auto mt-6 max-w-xl text-lg text-white/80">Explore a smarter approach to industrial surface quality analysis.</p>
          <div className="mt-10 flex justify-center"><LimeButton to="/app" size="lg">Explore {BRAND.name}</LimeButton></div>
        </div>
      </Reveal>
    </section>
  );
}
