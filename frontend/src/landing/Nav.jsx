import { AnimatePresence, motion } from "framer-motion";
import { Menu, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Logo } from "../components/Logo.jsx";
import { BRAND } from "../brand.js";

const LINKS = [
  ["Platform", "#platform"],
  ["Technology", "#technology"],
  ["Solutions", "#solutions"],
  ["Research", "#research"],
];

/** Floating nav: transparent over the hero, turns into a white glass bar once the page scrolls. */
export default function Nav() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const on = () => setScrolled(window.scrollY > 24);
    on();
    window.addEventListener("scroll", on, { passive: true });
    return () => window.removeEventListener("scroll", on);
  }, []);

  return (
    <div className="fixed inset-x-0 top-0 z-50 flex justify-center px-4 pt-4">
      <motion.nav
        initial={{ y: -30, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        className={`flex w-full max-w-6xl items-center justify-between rounded-full px-3 py-2 pl-5 transition-all duration-500 ${
          scrolled ? "glass-white shadow-soft ring-1 ring-black/5" : "bg-transparent"}`}
        aria-label="Main"
      >
        <Link to="/" aria-label={`${BRAND.name} home`}><Logo dark={scrolled} /></Link>

        <ul className="hidden items-center gap-1 md:flex">
          {LINKS.map(([label, href]) => (
            <li key={label}>
              <a href={href} className={`rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                scrolled ? "text-brand-ink/70 hover:bg-brand/5 hover:text-brand-ink" : "text-white/80 hover:bg-white/10 hover:text-white"}`}>
                {label}
              </a>
            </li>
          ))}
        </ul>

        <div className="hidden items-center gap-2 md:flex">
          <Link to="/app" className={`rounded-full px-4 py-2 text-sm font-medium transition-colors ${
            scrolled ? "text-brand-ink/80 hover:text-brand-ink" : "text-white/85 hover:text-white"}`}>
            Sign In
          </Link>
          <Link to="/app" className="rounded-full bg-lime px-5 py-2.5 text-sm font-semibold text-brand-ink shadow-lime transition-transform duration-300 hover:-translate-y-0.5">
            Get Started
          </Link>
        </div>

        <button className={`grid h-10 w-10 place-items-center rounded-full md:hidden ${scrolled ? "text-brand-ink" : "text-white"}`}
                onClick={() => setOpen((v) => !v)} aria-label={open ? "Close menu" : "Open menu"} aria-expanded={open}>
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </motion.nav>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}
            className="glass-white absolute inset-x-4 top-[76px] rounded-3xl p-3 shadow-float ring-1 ring-black/5 md:hidden"
          >
            {LINKS.map(([label, href]) => (
              <a key={label} href={href} onClick={() => setOpen(false)} className="block rounded-2xl px-4 py-3 font-medium text-brand-ink hover:bg-brand/5">{label}</a>
            ))}
            <div className="mt-2 flex gap-2 border-t border-black/5 p-2 pt-3">
              <Link to="/app" className="flex-1 rounded-full px-4 py-3 text-center font-medium text-brand-ink ring-1 ring-black/10">Sign In</Link>
              <Link to="/app" className="flex-1 rounded-full bg-lime px-4 py-3 text-center font-semibold text-brand-ink">Get Started</Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
