import { useEffect, useState } from "react";
import { Link, NavLink, Route, Routes } from "react-router-dom";
import { api } from "./api.js";
import { LogoMark } from "./components/Logo.jsx";
import { BRAND } from "./brand.js";
import Overview from "./pages/Overview.jsx";
import Inspect from "./pages/Inspect.jsx";
import Batch from "./pages/Batch.jsx";
import Analytics from "./pages/Analytics.jsx";
import History from "./pages/History.jsx";
import ModelPerformance from "./pages/ModelPerformance.jsx";
import Reports from "./pages/Reports.jsx";
import "./styles.css";

const NAV = [
  ["/app", "Factory Overview"],
  ["/app/inspect", "Image Inspection"],
  ["/app/batch", "Batch & Line Simulation"],
  ["/app/analytics", "Defect Analytics"],
  ["/app/history", "Inspection History"],
  ["/app/models", "Model Performance"],
  ["/app/reports", "Reports"],
];

/** Operations console: the seven inspection modules, served under /app. */
export default function Console() {
  const [health, setHealth] = useState(null);
  useEffect(() => {
    const prev = document.title;
    document.title = `${BRAND.name} - Inspection console`;
    return () => { document.title = prev; };
  }, []);
  useEffect(() => { api.health().then(setHealth).catch(() => setHealth({ status: "down" })); }, []);

  return (
    <div className="shell">
      <aside className="sidebar">
        <Link className="brand" to="/" title="Back to website">
          <LogoMark size={32} />
          <div>
            <div className="brand-name">{BRAND.name}</div>
            <div className="brand-sub">{BRAND.maker}</div>
          </div>
        </Link>
        <nav className="nav">
          {NAV.map(([to, label], i) => (
            <NavLink key={to} to={to} end={to === "/app"}><span className="num">{i + 1}</span>{label}</NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div>
            API:{" "}
            <span style={{ color: health?.status === "ok" ? "#D8FF4F" : "#ff8a80", fontWeight: 600 }}>
              {health ? health.status : "…"}
            </span>
          </div>
          {health?.default_model && <div>Model: <code>{health.default_model}</code></div>}
          {health?.policy_version && <div>Policy: v{health.policy_version}</div>}
          <div style={{ marginTop: 8 }}><Link to="/">← Website</Link> · {BRAND.descriptor}</div>
        </div>
      </aside>
      <main className="main">
        <Routes>
          <Route index element={<Overview />} />
          <Route path="inspect" element={<Inspect />} />
          <Route path="batch" element={<Batch />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="history" element={<History />} />
          <Route path="models" element={<ModelPerformance />} />
          <Route path="reports" element={<Reports />} />
          <Route path="*" element={<Overview />} />
        </Routes>
      </main>
    </div>
  );
}
