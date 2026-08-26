/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        mist: {
          50: "#fbfafc",
          100: "#f4f2f7",
          200: "#ebe7f0",
          300: "#ddd7e6",
        },
        wine: {
          50: "#f8f1f0",
          100: "#eedddd",
          400: "#a35d57",
          500: "#7a4440",
          600: "#6b3a38",
          700: "#542e2c",
          800: "#3d2221",
        },
        lagoon: {
          100: "#e8f4f5",
          200: "#cfe6e8",
          300: "#a8cfd1",
          400: "#7fb6ba",
          500: "#5a9a9f",
        },
        ink: {
          700: "#2a2b22",
          800: "#1c1d17",
          900: "#141510",
          950: "#0c0d0b",
        },
        copper: {
          300: "#e2b07a",
          400: "#c98a45",
          500: "#b56f28",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      boxShadow: {
        soft: "0 12px 40px rgba(61, 34, 33, 0.08)",
        lift: "0 8px 24px rgba(61, 34, 33, 0.06)",
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
          "50%": { opacity: "0.7" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.45s ease-out both",
        "fade-in": "fade-in 0.35s ease-out both",
        "soft-pulse": "soft-pulse 2s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
