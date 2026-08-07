/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: { 50: '#e4f6f6', 100: '#c6ebec', 200: '#9bdcdf', 300: '#6fc7cb', 400: '#0c969c', 500: '#0a7075', 600: '#086166', 700: '#064b4f', 800: '#032f30', 900: '#031716', 950: '#031716' },
        'brand-deep': { 50: '#e8f5f5', 100: '#c8e9e9', 200: '#9bd7d9', 300: '#65bec1', 400: '#0c969c', 500: '#0a7075', 600: '#086166', 700: '#064c50', 800: '#032f30', 900: '#031716', 950: '#031716' },
        'brand-blue': { 50: '#eef4f7', 100: '#d7e8f0', 200: '#b6d2e0', 300: '#6ba3be', 400: '#5286a0', 500: '#3d6e86', 600: '#274d60', 700: '#203f4e', 800: '#19313d', 900: '#102128', 950: '#091519' },
        'brand-mist': { 50: '#eef4f7', 100: '#d7e8f0', 200: '#b6d2e0', 300: '#6ba3be', 400: '#5286a0', 500: '#3d6e86', 600: '#274d60', 700: '#203f4e', 800: '#19313d', 900: '#102128', 950: '#091519' },
        rose: { 50: '#e4f6f6', 100: '#c6ebec', 200: '#9bdcdf', 300: '#6fc7cb', 400: '#0c969c', 500: '#0a7075', 600: '#086166', 700: '#064b4f', 800: '#032f30', 900: '#031716', 950: '#031716' },
        fuchsia: { 50: '#e8f5f5', 100: '#c8e9e9', 200: '#9bd7d9', 300: '#65bec1', 400: '#0c969c', 500: '#0a7075', 600: '#086166', 700: '#064c50', 800: '#032f30', 900: '#031716', 950: '#031716' },
        violet: { 50: '#eef4f7', 100: '#d7e8f0', 200: '#b6d2e0', 300: '#6ba3be', 400: '#5286a0', 500: '#3d6e86', 600: '#274d60', 700: '#203f4e', 800: '#19313d', 900: '#102128', 950: '#091519' },
        amber: { 50: '#eef4f7', 100: '#d7e8f0', 200: '#b6d2e0', 300: '#6ba3be', 400: '#5286a0', 500: '#3d6e86', 600: '#274d60', 700: '#203f4e', 800: '#19313d', 900: '#102128', 950: '#091519' },
      },
      fontFamily: {
        sans: ['Manrope', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        display: ['Space Grotesk', 'Manrope', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        glass: '0 24px 84px rgba(3, 23, 22, 0.52)',
        brand: '0 0 38px rgba(12, 150, 156, 0.20)',
        orchid: '0 0 44px rgba(107, 163, 190, 0.20)',
      },
      animation: {
        'orb-float': 'orbFloat 6s ease-in-out infinite',
        'orb-spin': 'orbSpin 14s linear infinite',
        'orb-spin-reverse': 'orbSpinReverse 18s linear infinite',
        'pulse-soft': 'pulseSoft 3.4s ease-in-out infinite',
        'message-in': 'messageIn 240ms cubic-bezier(.22,1,.36,1) both',
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
          from: { opacity: '0', transform: 'translateY(8px) scale(.99)' },
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
