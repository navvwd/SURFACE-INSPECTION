import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App.jsx";
import "./index.css";

// Shows the error instead of a blank white page if anything fails while rendering.
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }
  static getDerivedStateFromError(error) {
    return { error };
  }
  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div style={{ padding: 32, fontFamily: "system-ui, sans-serif", color: "#e3e8ec", background: "#0f1418", minHeight: "100vh" }}>
        <h2>COCO SurfaceCheck hit an error while rendering</h2>
        <pre style={{ whiteSpace: "pre-wrap", color: "#e5534b" }}>{String(this.state.error?.stack || this.state.error)}</pre>
        <button onClick={() => { try { localStorage.clear(); } catch { /* ignore */ } location.reload(); }}>Reset and reload</button>
      </div>
    );
  }
}

document.getElementById("root").dataset.mounted = "1";
ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ErrorBoundary>
      <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <App />
      </BrowserRouter>
    </ErrorBoundary>
  </React.StrictMode>
);
