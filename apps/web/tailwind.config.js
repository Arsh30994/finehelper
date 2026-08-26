/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        mist: {
          50: "#080808",
          100: "#111111",
          200: "#1a1a1a",
          300: "#2c2c2c",
        },
        /* Muted metallic gold / bronze accent */
        wine: {
          50: "#1a1610",
          100: "#2a2318",
          400: "#d4b483",
          500: "#c29d6d",
          600: "#a98455",
          700: "#8f6e45",
          800: "#6f5436",
        },
        lagoon: {
          100: "#152018",
          200: "#1c2a20",
          300: "#2a4032",
          400: "#3d5c48",
          500: "#4a7c59",
        },
        ink: {
          700: "#b0b0b0",
          800: "#e8e8e8",
          900: "#fafafa",
          950: "#ffffff",
        },
        copper: {
          300: "#e0c9a0",
          400: "#d4b483",
          500: "#c29d6d",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "ui-sans-serif", "system-ui"],
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      boxShadow: {
        soft: "0 0 0 1px rgba(194,157,109,0.08), 0 12px 40px rgba(0,0,0,0.55)",
        lift: "0 4px 20px rgba(0,0,0,0.45)",
        glow: "0 0 28px rgba(194,157,109,0.18)",
      },
      borderRadius: {
        xl2: "1.25rem",
        xl3: "1.75rem",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        "soft-pulse": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.72" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.45s ease-out both",
        "fade-in": "fade-in 0.35s ease-out both",
        "soft-pulse": "soft-pulse 2.4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
