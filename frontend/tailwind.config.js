/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        jarvis: {
          bg: "#060b14",
          panel: "#0b1220",
          elevated: "#101a2c",
          border: "#1c3a5a",
          muted: "#7a93b0",
          text: "#e6f4ff",
          accent: "#00e5ff",
          accentDim: "#00a8c4",
          cyan: "#00f2ff",
          success: "#2dff9a",
          danger: "#ff5c7a",
          warn: "#ffc857",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "system-ui", "sans-serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      boxShadow: {
        glow: "0 0 40px rgba(0, 242, 255, 0.18)",
        "glow-sm": "0 0 18px rgba(0, 242, 255, 0.25)",
        "glow-lg": "0 0 80px rgba(0, 229, 255, 0.22)",
      },
      keyframes: {
        pulseDot: {
          "0%, 100%": { opacity: "0.35", transform: "scale(0.85)" },
          "50%": { opacity: "1", transform: "scale(1)" },
        },
        fadeIn: {
          from: { opacity: "0", transform: "translateY(6px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        spinSlow: {
          from: { transform: "rotate(0deg)" },
          to: { transform: "rotate(360deg)" },
        },
        spinReverse: {
          from: { transform: "rotate(360deg)" },
          to: { transform: "rotate(0deg)" },
        },
        orbPulse: {
          "0%, 100%": { opacity: "0.55", transform: "scale(1)" },
          "50%": { opacity: "1", transform: "scale(1.04)" },
        },
        wave: {
          "0%, 100%": { height: "18%" },
          "50%": { height: "100%" },
        },
      },
      animation: {
        pulseDot: "pulseDot 1.2s ease-in-out infinite",
        fadeIn: "fadeIn 0.35s ease-out",
        spinSlow: "spinSlow 18s linear infinite",
        spinReverse: "spinReverse 12s linear infinite",
        orbPulse: "orbPulse 2.4s ease-in-out infinite",
        wave: "wave 1s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
