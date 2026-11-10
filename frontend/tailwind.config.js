/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  // Preflight is off so Tailwind's global reset cannot alter the existing dashboard (styles.css).
  // The marketing site applies its own scoped reset in src/index.css (.site).
  corePlugins: { preflight: false },
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: "#087FC4", deep: "#075B96", electric: "#16A9F5", ink: "#111827", soft: "#F5F7FA", navy: "#04223A" },
        lime: { DEFAULT: "#D8FF4F", dark: "#B8E21F" },
      },
      fontFamily: {
        display: ['"Space Grotesk"', "Inter", "system-ui", "sans-serif"],
        sans: ["Inter", "system-ui", "-apple-system", '"Segoe UI"', "sans-serif"],
        mono: ['"IBM Plex Mono"', "ui-monospace", "Consolas", "monospace"],
      },
      boxShadow: {
        float: "0 30px 60px -20px rgba(4, 34, 58, 0.45), 0 12px 24px -12px rgba(4, 34, 58, 0.25)",
        soft: "0 1px 2px rgba(17,24,39,.04), 0 8px 24px -8px rgba(17,24,39,.10)",
        lime: "0 10px 30px -8px rgba(216, 255, 79, 0.65)",
      },
      borderRadius: { "4xl": "2rem" },
    },
  },
  plugins: [],
};
