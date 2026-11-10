// Thin fetch wrapper around the FastAPI backend. All data shown in the UI comes from these calls.

async function request(path, options = {}) {
  const res = await fetch(path, options);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch { /* non-JSON error */ }
    throw new Error(`${res.status}: ${detail}`);
  }
  return res.json();
}

const qs = (params = {}) => {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") p.append(k, v);
  });
  const s = p.toString();
  return s ? `?${s}` : "";
};

export const api = {
  health: () => request("/api/health"),
  overview: () => request("/api/analytics/overview"),
  defects: (params) => request(`/api/analytics/defects${qs(params)}`),
  models: () => request("/api/models"),
  model: (name, version) => request(`/api/models/${name}/${version}`),
  comparison: () => request("/api/comparison"),
  policy: () => request("/api/policy"),
  inspections: (params) => request(`/api/inspections${qs(params)}`),
  inspection: (id) => request(`/api/inspections/${id}`),
  inspect: (file, { productId, batchId, model }) => {
    const fd = new FormData();
    fd.append("file", file);
    if (productId) fd.append("product_id", productId);
    if (batchId) fd.append("batch_id", batchId);
    if (model) fd.append("model", model);
    return request("/api/inspections", { method: "POST", body: fd });
  },
  review: (id, body) =>
    request(`/api/inspections/${id}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  batches: () => request("/api/batches"),
  batch: (id) => request(`/api/batches/${id}`),
  createBatch: (files, { productLine, model, pacingMs, productPrefix }) => {
    const fd = new FormData();
    files.forEach((f) => fd.append("files", f));
    if (productLine) fd.append("product_line", productLine);
    if (model) fd.append("model", model);
    fd.append("pacing_ms", String(pacingMs ?? 0));
    if (productPrefix) fd.append("product_prefix", productPrefix);
    return request("/api/batches", { method: "POST", body: fd });
  },
  simulate: (body) =>
    request("/api/batches/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  runBatchUrl: (id) => `/api/batches/${id}/run`,
  csvUrl: (params) => `/api/reports/inspections.csv${qs(params)}`,
  inspectionPdfUrl: (id) => `/api/reports/inspections/${id}.pdf`,
  batchPdfUrl: (id) => `/api/reports/batches/${id}.pdf`,
};
