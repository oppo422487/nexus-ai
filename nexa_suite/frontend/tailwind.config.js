/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        "nexa-bg": "#020617",
        "nexa-panel": "#07111F",
        "nexa-card": "#0B1628",
        "nexa-cyan": "#00E5FF",
        "nexa-blue": "#2563EB",
        "nexa-purple": "#8B5CF6",
        "nexa-green": "#22C55E",
        "nexa-red": "#EF4444",
        "nexa-text": "#E6F1FF",
        "nexa-muted": "#94A3B8"
      }
    }
  },
  plugins: []
};