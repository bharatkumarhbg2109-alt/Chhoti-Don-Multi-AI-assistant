/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Manrope', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        display: ['Space Grotesk', 'Manrope', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        glass: '0 24px 84px rgba(4, 3, 7, 0.52)',
        brand: '0 0 38px rgba(244, 63, 94, 0.20)',
        orchid: '0 0 44px rgba(217, 70, 239, 0.20)',
      },
      animation: {
        'orb-float': 'orbFloat 6s ease-in-out infinite',
        'orb-spin': 'orbSpin 14s linear infinite',
        'orb-spin-reverse': 'orbSpinReverse 18s linear infinite',
        'pulse-soft': 'pulseSoft 3.4s ease-in-out infinite',
        'message-in': 'messageIn 520ms cubic-bezier(.2,.8,.2,1) both',
        shimmer: 'shimmer 1.8s linear infinite',
        'gradient-shift': 'gradientShift 10s ease infinite',
        'ping-slow': 'pingSlow 2.6s cubic-bezier(0,0,.2,1) infinite',
      },
      keyframes: {
        orbFloat: {
          '0%, 100%': { transform: 'translateY(0) scale(1)' },
          '50%': { transform: 'translateY(-10px) scale(1.025)' },
        },
        orbSpin: {
          from: { transform: 'rotate(0deg)' },
          to: { transform: 'rotate(360deg)' },
        },
        orbSpinReverse: {
          from: { transform: 'rotate(360deg)' },
          to: { transform: 'rotate(0deg)' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '.42', transform: 'scale(.94)' },
          '50%': { opacity: '.9', transform: 'scale(1.06)' },
        },
        messageIn: {
          from: { opacity: '0', transform: 'translateY(14px) scale(.985)' },
          to: { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
        shimmer: {
          from: { backgroundPosition: '200% 0' },
          to: { backgroundPosition: '-200% 0' },
        },
        gradientShift: {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        pingSlow: {
          '75%, 100%': { transform: 'scale(1.8)', opacity: '0' },
        },
      },
    },
  },
  plugins: [],
};
