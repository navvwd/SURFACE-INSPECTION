import { Link } from "react-router-dom";
import { Logo } from "../components/Logo.jsx";
import { BRAND } from "../brand.js";

const COLS = [
  ["Product", [["Inspection console", "/app"], ["Image inspection", "/app/inspect"], ["Batch simulation", "/app/batch"], ["Reports", "/app/reports"]]],
  ["Technology", [["Custom CNN", "#technology"], ["ResNet18", "#technology"], ["Grad-CAM", "#technology"], ["Research results", "#research"]]],
  ["About", [["Platform", "#platform"], ["Solutions", "#solutions"], ["Model performance", "/app/models"], ["Technical report", "/artifacts/FINAL_REPORT.md"]]],
];

function FooterLink({ to, children }) {
  const cls = "text-sm text-white/60 transition-colors hover:text-lime";
  return to.startsWith("/app") ? <Link to={to} className={cls}>{children}</Link> : <a href={to} className={cls}>{children}</a>;
}

export default function Footer() {
  return (
    <footer className="bg-brand-navy px-5 pb-10 pt-20 text-white">
      <div className="mx-auto max-w-6xl">
        <div className="grid gap-12 md:grid-cols-[1.4fr_repeat(4,1fr)]">
          <div>
            <Logo sub />
            <p className="mt-5 max-w-xs font-display text-lg font-medium text-white">{BRAND.tagline}</p>
            <p className="mt-2 max-w-xs text-sm leading-relaxed text-white/55">{BRAND.descriptor} software by {BRAND.company}.</p>
          </div>
          {COLS.map(([title, links]) => (
            <div key={title}>
              <h4 className="font-display text-sm font-semibold text-white">{title}</h4>
              <ul className="mt-4 space-y-2.5">{links.map(([l, to]) => <li key={l}><FooterLink to={to}>{l}</FooterLink></li>)}</ul>
            </div>
          ))}
          <div>
            <h4 className="font-display text-sm font-semibold text-white">Contact</h4>
            <p className="mt-4 text-sm leading-relaxed text-white/60">Questions about this project can be directed to the project author.</p>
          </div>
        </div>
        <div className="mt-16 flex flex-col gap-3 border-t border-white/10 pt-6 text-xs text-white/45 md:flex-row md:items-center md:justify-between">
          <span>Project information: academic Deep Learning mini-project · NEU-CLS steel surface dataset · not a commercial product.</span>
          <span>© {new Date().getFullYear()} {BRAND.company} · {BRAND.name}</span>
        </div>
      </div>
    </footer>
  );
}
