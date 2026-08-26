/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Hanken Grotesk"', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
        display: ['"JetBrains Mono"', 'monospace'],
      },
      colors: {
        background: '#0c141f',
        'surface-lowest': '#070e19',
        'surface-low': '#151c27',
        'surface-container': '#19202b',
        'surface-high': '#232a36',
        'surface-highest': '#2e3541',
        'surface-bright': '#323946',
        'border-tactical': '#232a36',
        'border-outline': '#374151',
        'border-dim': '#1c2430',
        'on-surface': '#dce2f3',
        'on-surface-variant': '#c5c6cb',
        'outline-variant': '#45474a',
        'tactical-primary': '#c3c7cd',
        'tactical-blue': '#38bdf8',
        'tactical-red': '#ef4444',
        'tactical-orange': '#f97316',
        'tactical-yellow': '#eab308',
        'tactical-green': '#10b981',
        'tactical-cyan': '#06b6d4',
      },
      borderRadius: {
        none: '0',
        sm: '2px',
        DEFAULT: '4px',
        md: '4px',
        lg: '6px',
      },
      spacing: {
        'unit': '4px',
        'gutter': '8px',
        'panel-padding': '12px',
        'container-margin': '16px',
      },
    },
  },
  plugins: [],
}
