/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          darkest: '#0a0a0a',
          dark: '#121212',
          card: '#1e1e1e',
          border: '#2c2c2c',
          muted: '#8e8e93',
          emerald: '#10b981',
          crimson: '#f43f5e',
          amber: '#f59e0b',
          sky: '#0ea5e9'
        }
      },
      fontFamily: {
        sans: ['var(--font-sans)', 'sans-serif'],
      },
      boxShadow: {
        'glass': '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
      }
    },
  },
  plugins: [],
};
