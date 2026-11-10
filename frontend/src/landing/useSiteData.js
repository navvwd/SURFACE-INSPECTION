import { useEffect, useState } from "react";

/**
 * Data for the marketing site.
 *  - brand: real model outputs on held-out test images (public/brand/brand.json, made by scripts/make_brand_assets.py)
 *  - overview / batch / models: LIVE data from the running API.
 * When the API is unreachable, `live` is false and cards must label themselves as a demo preview.
 */
export function useSiteData() {
  const [state, setState] = useState({ brand: null, overview: null, batch: null, models: null, live: false, loaded: false });

  useEffect(() => {
    let alive = true;
    const get = (url) => fetch(url).then((r) => (r.ok ? r.json() : null)).catch(() => null);
    (async () => {
      const [brand, overview, batches, models] = await Promise.all([
        get("/brand/brand.json"), get("/api/analytics/overview"), get("/api/batches"), get("/api/models"),
      ]);
      let batch = null;
      if (Array.isArray(batches) && batches.length) {
        const latest = batches.find((b) => b.status === "completed") || batches[0];
        batch = await get(`/api/batches/${encodeURIComponent(latest.batch_id)}`);
      }
      if (alive) setState({ brand, overview, batch, models, live: !!overview, loaded: true });
    })();
    return () => { alive = false; };
  }, []);

  return state;
}

export const CLASS_LABEL = {
  Crazing: "Crazing", Inclusion: "Inclusion", Patches: "Patches",
  Pitted_Surface: "Pitted Surface", "Rolled-in_Scale": "Rolled-in Scale", Scratches: "Scratches",
};
