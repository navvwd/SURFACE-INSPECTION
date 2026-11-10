import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import Landing from "./landing/Landing.jsx";

// The operations console (dashboard) is code-split so the marketing site loads fast.
const Console = lazy(() => import("./Console.jsx"));

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route
        path="/app/*"
        element={
          <Suspense fallback={<div style={{ padding: 32, fontFamily: "Inter, sans-serif", color: "#5b6676" }}>Loading console…</div>}>
            <Console />
          </Suspense>
        }
      />
      <Route path="*" element={<Landing />} />
    </Routes>
  );
}
