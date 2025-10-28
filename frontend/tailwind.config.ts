import { type Config } from "tailwindcss";

export default {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // SMC Public Works Color Scheme
        primary: {
          DEFAULT: '#2563eb',
          foreground: '#ffffff',
        },
        accent: {
          DEFAULT: '#02a6e9',
          foreground: '#ffffff',
        },
        // Status colors for lessons learned
        severity: {
          high: '#e9202a',
          medium: '#f99810', 
          low: '#7aad34',
        },
        // Utility colors
        success: '#8dc63f',
        warning: '#faa634',
        error: '#b5121b',
        info: '#38939b',
        // Neutral colors
        background: '#ffffff',
        foreground: '#232323',
        card: {
          DEFAULT: '#ffffff',
          foreground: '#232323',
        },
        secondary: {
          DEFAULT: '#f4f4f5',
          foreground: '#232323',
        },
        muted: {
          DEFAULT: '#f4f4f5',
          foreground: '#6b7280',
        },
        border: '#e5e7eb',
        input: '#e5e7eb',
        ring: '#2563eb',
      },
      spacing: {
        xs: "0.25rem",
        sm: "0.5rem",
        md: "1rem",
        lg: "1.5rem",
        xl: "2rem",
        xxl: "3rem",
        xxxl: "4rem",
      },
    },
  },
  plugins: [],
} satisfies Config;
