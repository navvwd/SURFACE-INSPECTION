import { motion, useReducedMotion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { Link } from "react-router-dom";

/** Fade-and-rise when scrolled into view (respects prefers-reduced-motion). */
export function Reveal({ children, delay = 0, y = 28, className = "", as = "div" }) {
  const reduce = useReducedMotion();
  const M = motion[as];
  return (
    <M
      className={className}
      initial={reduce ? false : { opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.7, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </M>
  );
}

export function Eyebrow({ children, light = false }) {
  return (
    <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] ${
      light ? "bg-white/10 text-white/80 ring-1 ring-white/20" : "bg-brand/5 text-brand ring-1 ring-brand/15"}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-lime shadow-[0_0_0_3px_rgba(216,255,79,0.25)]" />
      {children}
    </span>
  );
}

const base = "group inline-flex items-center justify-center gap-2 rounded-full font-semibold transition-all duration-300 will-change-transform";
const sizes = { md: "h-11 px-5 text-sm", lg: "h-14 px-7 text-[15px]" };

/** Lime primary CTA - used sparingly (UI.MD). Renders a router Link, an anchor, or a button. */
export function LimeButton({ to, href, onClick, children, size = "md", className = "" }) {
  const cls = `${base} ${sizes[size]} bg-lime text-brand-ink shadow-lime hover:-translate-y-0.5 hover:bg-[#e2ff7a] ${className}`;
  const inner = <>{children}<ArrowRight className="h-4 w-4 transition-transform duration-300 group-hover:translate-x-1" /></>;
  if (to) return <Link to={to} className={cls}>{inner}</Link>;
  if (href) return <a href={href} className={cls}>{inner}</a>;
  return <button type="button" onClick={onClick} className={cls}>{inner}</button>;
}

export function GhostButton({ to, href, children, icon: Icon, size = "md", dark = false, className = "" }) {
  const tone = dark
    ? "text-brand-ink ring-1 ring-brand-ink/15 hover:ring-brand/40 hover:bg-brand/5"
    : "text-white ring-1 ring-white/35 hover:bg-white/10 hover:ring-white/60";
  const cls = `${base} ${sizes[size]} ${tone} hover:-translate-y-0.5 ${className}`;
  const inner = <>{Icon && <Icon className="h-4 w-4" />}{children}</>;
  if (to) return <Link to={to} className={cls}>{inner}</Link>;
  return <a href={href} className={cls}>{inner}</a>;
}

export const fmtInt = (n) => (n === null || n === undefined ? "—" : Number(n).toLocaleString());
