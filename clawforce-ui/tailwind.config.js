/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Söhne"', "system-ui", "-apple-system", "sans-serif"],
        mono: ['"Söhne Mono"', "ui-monospace", "monospace"],
      },
      colors: {
        claude: {
          bg: "#FAF9F6",
          surface: "#F0EDE6",
          "surface-alt": "#E8E2D9",
          hover: "#E3DDD4",
          border: "#DDD7CE",
          "border-strong": "#C5BEB5",
          input: "#FFFFFF",
          "text-primary": "#1A1A1A",
          "text-secondary": "#3D3833",
          "text-tertiary": "#6B6560",
          "text-muted": "#9B958F",
          accent: "#D97757",
          "accent-hover": "#C4633F",
          "accent-soft": "#FDF0EB",
          sidebar: "#EDE8DB",
          "sidebar-hover": "#E3DDD4",
          "sidebar-active": "#DDD7CE",
        },
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};
