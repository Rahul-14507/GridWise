/** @type {import('tailwindcss').Config} */
export default {
  // Tailwind scans all React source files for class usage.
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  // We force dark mode via a `dark` class strategy so the tech
  // slate aesthetic is always on (single-theme ops console).
  darkMode: 'class',
  theme: {
    extend: {
      // Brand palette: slate base, emerald = online/stable, amber = warning.
      colors: {
        grid: {
          bg: '#020617', // slate-950
          panel: '#0f172a', // slate-900
          card: '#1e293b', // slate-800
          border: '#334155', // slate-700
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        glowEmerald: '0 0 12px rgba(16, 185, 129, 0.45)',
        glowAmber: '0 0 12px rgba(245, 158, 11, 0.4)',
      },
    },
  },
  plugins: [],
};
