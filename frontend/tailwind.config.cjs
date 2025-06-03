/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          light: '#4da6ff',
          DEFAULT: '#0078ff',
          dark: '#0057b8',
        },
        chat: {
          background: '#020305',
          sidebar: '#141923',
          message: '#222834',
          text: '#f9fbfc',
          secondary: '#b6c2d1',
          muted: '#8f99ad',
          accent: '#00a9dd',
        },
      },
      fontFamily: {
        'hanken': ['Hanken Grotesk', 'sans-serif'],
        'inter': ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
