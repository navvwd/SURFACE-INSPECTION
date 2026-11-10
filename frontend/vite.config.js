import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const backend = process.env.SURFACECHECK_API || "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: { manualChunks: { react: ["react", "react-dom", "react-router-dom"], charts: ["recharts"] } },
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": { target: backend, changeOrigin: true },
      "/storage": { target: backend, changeOrigin: true },
      "/artifacts": { target: backend, changeOrigin: true },
    },
  },
});
