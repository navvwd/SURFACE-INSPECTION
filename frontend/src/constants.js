export const CLASSES = ["Crazing", "Inclusion", "Patches", "Pitted_Surface", "Rolled-in_Scale", "Scratches"];

// Categorical palette (distinguishable in light and dark themes).
export const CLASS_COLORS = {
  Crazing: "#4e9fd1",
  Inclusion: "#e0803a",
  Patches: "#8f7ad8",
  Pitted_Surface: "#3fb27f",
  "Rolled-in_Scale": "#d65c7a",
  Scratches: "#c9b03a",
};

export const DECISIONS = ["PASS_CANDIDATE", "REJECT_CANDIDATE", "MANUAL_REVIEW"];
export const DECISION_META = {
  PASS_CANDIDATE: { label: "Pass candidate", short: "PASS", color: "var(--pass)" },
  REJECT_CANDIDATE: { label: "Reject candidate", short: "REJECT", color: "var(--reject)" },
  MANUAL_REVIEW: { label: "Manual review", short: "REVIEW", color: "var(--review)" },
};
// Hex versions for Recharts (CSS variables are not resolved inside SVG fills on every browser).
export const DECISION_HEX = { PASS_CANDIDATE: "#3fb27f", REJECT_CANDIDATE: "#e5534b", MANUAL_REVIEW: "#e3a336" };

export const REVIEW_STATUS = {
  PENDING_REVIEW: "Pending review",
  PENDING_CONFIRMATION: "Awaiting confirmation",
  NOT_REQUIRED: "Not required",
  REVIEWED: "Reviewed",
};

export const pretty = (s) => (s || "").replaceAll("_", " ");
export const pct = (v, d = 1) => (v === null || v === undefined ? "—" : `${(v * 100).toFixed(d)}%`);
export const ms = (v, d = 1) => (v === null || v === undefined ? "—" : `${Number(v).toFixed(d)} ms`);
export const fmtTime = (iso) => (iso ? new Date(iso).toLocaleString() : "—");
