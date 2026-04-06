/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/providers/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  // Enable built-in RTL variant — generates [dir="rtl"] selectors automatically
  // Use `rtl:` prefix on any class: rtl:flex-row-reverse, rtl:text-right, etc.
  future: {
    hoverOnlyWhenSupported: true,
  },
  theme: {
    extend: {
      colors: {
        brand: {
          50:  "#eef7ff",
          100: "#d9edff",
          200: "#bce0ff",
          300: "#8eccff",
          400: "#59afff",
          500: "#338bff",
          600: "#1a6af5",
          700: "#1354e1",
          800: "#1644b6",
          900: "#183c8f",
          950: "#142657",
        },
        success: {
          50:  "#f0fdf4",
          500: "#22c55e",
          700: "#15803d",
        },
        warning: {
          50:  "#fffbeb",
          500: "#f59e0b",
          700: "#b45309",
        },
        danger: {
          50:  "#fef2f2",
          500: "#ef4444",
          700: "#b91c1c",
        },
      },
      fontFamily: {
        sans:    ["Inter", "system-ui", "sans-serif"],
        arabic:  ["Tajawal", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
