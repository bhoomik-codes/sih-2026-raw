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
        sans:    ['"Hanken Grotesk"', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono:    ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
        display: ['"Orbitron"', '"JetBrains Mono"', 'monospace'],
      },
      colors: {
        /* Legacy surface tokens */
        background:            '#020810',
        'surface-lowest':      '#000d1a',
        'surface-low':         '#050f20',
        'surface-container':   '#0a1628',
        'surface-high':        '#0f1e34',
        'surface-highest':     '#152540',
        'surface-bright':      '#1a2c4a',
        'border-tactical':     'rgba(0,212,255,0.15)',
        'border-outline':      'rgba(0,212,255,0.3)',
        'border-dim':          'rgba(0,212,255,0.08)',
        'on-surface':          '#c8d6f0',
        'on-surface-variant':  '#8fa8cc',
        'outline-variant':     'rgba(0,212,255,0.25)',

        /* IBVAP Tactical Accent Palette */
        'accent-cyan':   '#00d4ff',
        'accent-amber':  '#ffb800',
        'accent-green':  '#00ff88',
        'accent-red':    '#ff3232',
        'accent-purple': '#a855f7',

        /* Severity */
        'tactical-primary': '#c8d6f0',
        'tactical-blue':    '#00d4ff',
        'tactical-red':     '#ff3232',
        'tactical-orange':  '#ff8c00',
        'tactical-yellow':  '#ffb800',
        'tactical-green':   '#00ff88',
        'tactical-cyan':    '#00d4ff',
      },
      borderRadius: {
        none: '0',
        sm:   '2px',
        DEFAULT: '4px',
        md:   '4px',
        lg:   '6px',
      },
      spacing: {
        'unit':             '4px',
        'gutter':           '8px',
        'panel-padding':    '10px',
        'container-margin': '12px',
      },
      keyframes: {
        'scanline-sweep': {
          '0%':   { top: '-60%' },
          '100%': { top: '110%' },
        },
        'border-glow-pulse': {
          '0%,100%': { borderColor: 'rgba(0,212,255,0.3)' },
          '50%':     { borderColor: 'rgba(0,212,255,0.7)' },
        },
        'ping-slow': {
          '0%,100%': { opacity: '0.5', transform: 'scale(1)' },
          '50%':     { opacity: '0', transform: 'scale(1.4)' },
        },
      },
      animation: {
        'border-glow':    'border-glow-pulse 3s ease-in-out infinite',
        'ping-slow':      'ping-slow 2.2s ease-in-out infinite',
        'scanline-sweep': 'scanline-sweep 5s linear infinite',
      },
    },
  },
  plugins: [],
}
