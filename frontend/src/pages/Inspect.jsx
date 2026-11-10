import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import InspectionDetail from "../components/InspectionDetail.jsx";
import { AcademicNotice, ErrorMsg, ModelSelect, useApi } from "../components/ui.jsx";

export default function Inspect() {
  const models = useApi(() => api.models());
  const [model, setModel] = useState("");
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [productId, setProductId] = useState("");
  const [batchId, setBatchId] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [over, setOver] = useState(false);
  const input = useRef();

  useEffect(() => {
    if (!model && models.data?.length) setModel((models.data.find((m) => m.is_default) || models.data[0]).key);
  }, [models.data, model]);
  useEffect(() => () => preview && URL.revokeObjectURL(preview), [preview]);

  const pick = (f) => {
    if (!f) return;
    setFile(f); setResult(null); setError(null);
    setPreview(URL.createObjectURL(f));
  };

  const run = async () => {
    setBusy(true); setError(null);
    try { setResult(await api.inspect(file, { productId, batchId, model })); }
    catch (e) { setError(e); } finally { setBusy(false); }
  };

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Individual Image Inspection</h1>
          <p>Upload one steel-surface image. The model input contract is a 200×200 grayscale image; other sizes or colour images are converted but routed to manual review.</p>
        </div>
      </div>
      <div className="grid g3" style={{ alignItems: "start" }}>
        <div className="card grid" style={{ gap: 12 }}>
          <div
            className={`drop${over ? " over" : ""}`}
            onClick={() => input.current.click()}
            onDragOver={(e) => { e.preventDefault(); setOver(true); }}
            onDragLeave={() => setOver(false)}
            onDrop={(e) => { e.preventDefault(); setOver(false); pick(e.dataTransfer.files[0]); }}
          >
            {preview ? (
              <img src={preview} alt="selected" style={{ maxWidth: "100%", maxHeight: 220, imageRendering: "pixelated" }} />
            ) : (
              <>Drop an image here or click to choose<br /><span className="small">PNG · BMP · JPG · TIFF</span></>
            )}
          </div>
          <input ref={input} type="file" accept="image/*,.bmp,.tif,.tiff" hidden onChange={(e) => pick(e.target.files[0])} />
          {file && <div className="small muted">{file.name} · {(file.size / 1024).toFixed(1)} KB</div>}
          <label className="field">Product ID (blank = auto-generate)<input value={productId} onChange={(e) => setProductId(e.target.value)} placeholder="e.g. COIL-24-0815" /></label>
          <label className="field">Batch ID (optional)<input value={batchId} onChange={(e) => setBatchId(e.target.value)} placeholder="e.g. HR-LINE2-SHIFT-A" /></label>
          <ModelSelect models={models.data} value={model} onChange={setModel} />
          <button className="primary" disabled={!file || busy} onClick={run}>{busy ? "Inspecting…" : "Run inspection"}</button>
          <ErrorMsg error={error} />
          <div className="small muted">Tip: test images from <code>dataset/raw/NEU-CLS</code> that are listed in <code>dataset/splits/test.csv</code> were never seen during training.</div>
        </div>
        <div className="span2">
          {result ? (
            <div className="card"><InspectionDetail data={result} onReviewed={setResult} /></div>
          ) : (
            <div className="card"><div className="muted" style={{ padding: 40, textAlign: "center" }}>Result, Grad-CAM heatmap and decision appear here.</div></div>
          )}
        </div>
      </div>
      <div style={{ marginTop: 16 }}><AcademicNotice /></div>
    </>
  );
}
