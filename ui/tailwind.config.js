/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{html,ts}",
  ],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Clash Display"', '"DM Sans"', 'sans-serif'],
        body: ['"DM Sans"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      colors: {
        // Custom palette — warm neutrals + electric accents
        surface: {
          50: '#FAF9F7',
          100: '#F3F1ED',
          200: '#E8E4DC',
          800: '#1C1917',
          900: '#0F0E0D',
          950: '#080706',
        },
        accent: {
          DEFAULT: '#6366F1',  // Indigo-electric
          light: '#818CF8',
          dark: '#4338CA',
          glow: 'rgba(99, 102, 241, 0.15)',
        },
        success: '#22C55E',
        warning: '#F59E0B',
        danger: '#EF4444',
      },
      backgroundImage: {
        'grid-pattern': 'radial-gradient(circle, rgba(99,102,241,0.08) 1px, transparent 1px)',
        'glow-gradient': 'radial-gradient(ellipse at center, rgba(99,102,241,0.12) 0%, transparent 70%)',
      },
      backgroundSize: {
        'grid-20': '20px 20px',
      },
      boxShadow: {
        'card': '0 1px 3px rgba(0,0,0,0.06), 0 8px 24px rgba(0,0,0,0.04)',
        'card-hover': '0 4px 12px rgba(0,0,0,0.08), 0 16px 40px rgba(0,0,0,0.06)',
        'glow': '0 0 30px rgba(99,102,241,0.12)',
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-out forwards',
        'slide-up': 'slideUp 0.5s ease-out forwards',
        'pulse-soft': 'pulseSoft 2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
      },
    },
  },
  plugins: [],
}
