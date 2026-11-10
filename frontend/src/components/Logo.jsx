import { BRAND } from "../brand.js";

// COCO SurfaceCheck mark: an inspection aperture (lens) over a steel strip with a scan line.
export function LogoMark({ size = 32, className = "" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" className={className} aria-hidden="true">
      <defs>
        <linearGradient id="sc-g" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#16A9F5" />
          <stop offset="1" stopColor="#075B96" />
        </linearGradient>
      </defs>
      <rect width="40" height="40" rx="11" fill="url(#sc-g)" />
      <path d="M7 20c3.6-6 8-9 13-9s9.4 3 13 9c-3.6 6-8 9-13 9S10.6 26 7 20Z" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinejoin="round" />
      <circle cx="20" cy="20" r="4.6" fill="#D8FF4F" />
      <path d="M6 30.5h28" stroke="#fff" strokeOpacity=".45" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M20 8.5v4M20 27.5v4" stroke="#fff" strokeOpacity=".7" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

/** Wordmark: "COCO SurfaceCheck" with an optional "A COCO MEDIA PRODUCT" line. */
export function Logo({ dark = false, sub = false, className = "" }) {
  const [a, b] = BRAND.wordmark;
  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <LogoMark />
      <span className="flex flex-col leading-none">
        <span className={`font-display text-[17px] font-semibold tracking-tight ${dark ? "text-brand-ink" : "text-white"}`}>
          {a} <span className={dark ? "text-brand" : "text-lime"}>{b}</span>
        </span>
        {sub && (
          <span className={`mt-1 text-[9.5px] font-semibold uppercase tracking-[0.2em] ${dark ? "text-brand-ink/50" : "text-white/55"}`}>
            {BRAND.maker}
          </span>
        )}
      </span>
    </span>
  );
}
