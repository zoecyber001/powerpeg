/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        // Instruments, not SaaS: IBM Plex was drawn for machine-facing interfaces.
        sans: ['"IBM Plex Sans"', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      colors: {
        // One warm neutral ramp, tinted toward paper and graphite ink.
        paper: '#F4F1EC',
        surface: '#FFFFFF',
        ink: '#1D1B17',
        'ink-2': '#57514A',
        'ink-3': '#6F6960',
        'ink-4': '#9C948A',
        line: '#E5DFD6',
        'line-strong': '#D2C9BD',
        // The single accent: the amber of a live indicator lamp.
        brass: '#A9721C',
        'brass-soft': '#F4EAD8',
        'brass-ink': '#7C5210',
        // Semantics only: a real incident, and a settled folio.
        brick: '#9E3B2E',
        'brick-soft': '#F7E9E5',
        'brick-ink': '#7E2C21',
        moss: '#3F6B52',
        'moss-soft': '#E8EFE9',
      },
      borderRadius: {
        control: '8px',
        panel: '10px',
        card: '12px',
      },
      boxShadow: {
        // Hairlines carry the depth; these are the only shadows in the system.
        card: '0 1px 0 0 rgba(29, 27, 23, 0.04)',
        pop: '0 12px 32px -12px rgba(29, 27, 23, 0.28)',
      },
      keyframes: {
        rise: {
          '0%': { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'none' },
        },
      },
      animation: {
        rise: 'rise 180ms cubic-bezier(0.2, 0.7, 0.3, 1) both',
      },
    },
  },
  plugins: [],
}
