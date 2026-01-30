/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Modern SaaS dark palette (Linear/Raycast inspired)
        gray: {
          950: "#09090b",
          900: "#0c0c0e",
          850: "#111113",
          800: "#18181b",
          750: "#1f1f23",
          700: "#27272a",
          600: "#3f3f46",
          500: "#52525b",
          400: "#71717a",
          300: "#a1a1aa",
          200: "#d4d4d8",
          100: "#e4e4e7",
          50: "#fafafa",
        },
        accent: {
          DEFAULT: "#6366f1", // Indigo
          hover: "#818cf8",
          muted: "#6366f120",
          subtle: "#6366f110",
        },
        success: "#22c55e",
        warning: "#eab308",
        error: "#ef4444",
      },
      fontFamily: {
        sans: [
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        mono: ["JetBrains Mono", "SF Mono", "Monaco", "monospace"],
      },
      fontSize: {
        "2xs": ["0.625rem", { lineHeight: "0.875rem" }],
      },
      boxShadow: {
        glow: "0 0 20px rgba(99, 102, 241, 0.15)",
        "glow-lg": "0 0 40px rgba(99, 102, 241, 0.2)",
        subtle: "0 1px 2px rgba(0, 0, 0, 0.3), 0 1px 3px rgba(0, 0, 0, 0.15)",
        elevated: "0 4px 12px rgba(0, 0, 0, 0.4), 0 0 1px rgba(0, 0, 0, 0.3)",
        float: "0 8px 30px rgba(0, 0, 0, 0.5), 0 0 1px rgba(0, 0, 0, 0.3)",
      },
      backgroundImage: {
        "gradient-radial":
          "radial-gradient(ellipse at center, var(--tw-gradient-stops))",
        "gradient-subtle":
          "linear-gradient(to bottom, rgba(99, 102, 241, 0.03), transparent)",
        noise:
          "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E\")",
      },
      animation: {
        "fade-in": "fadeIn 0.2s ease-out",
        "slide-up": "slideUp 0.3s ease-out",
        "slide-in-right": "slideInRight 0.3s ease-out",
        "pulse-subtle": "pulseSubtle 2s ease-in-out infinite",
        gradient: "gradient 8s linear infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideInRight: {
          "0%": { opacity: "0", transform: "translateX(16px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        pulseSubtle: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.5" },
        },
        gradient: {
          "0%, 100%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
        },
      },
      typography: {
        DEFAULT: {
          css: {
            maxWidth: "none",
            color: "#d4d4d8",
            a: {
              color: "#818cf8",
              textDecoration: "none",
              "&:hover": {
                color: "#a5b4fc",
              },
            },
            strong: { color: "#fafafa" },
            code: {
              color: "#a5b4fc",
              backgroundColor: "#27272a",
              padding: "2px 6px",
              borderRadius: "4px",
              fontWeight: "400",
              fontSize: "0.875em",
            },
            "code::before": { content: '""' },
            "code::after": { content: '""' },
            pre: {
              backgroundColor: "#0c0c0e",
              border: "1px solid #27272a",
              borderRadius: "8px",
            },
            h1: { color: "#fafafa", fontWeight: "600" },
            h2: { color: "#fafafa", fontWeight: "600" },
            h3: { color: "#fafafa", fontWeight: "600" },
            h4: { color: "#e4e4e7", fontWeight: "600" },
            blockquote: {
              color: "#a1a1aa",
              borderLeftColor: "#3f3f46",
            },
            hr: { borderColor: "#27272a" },
            "ul > li::marker": { color: "#52525b" },
            "ol > li::marker": { color: "#52525b" },
          },
        },
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};
