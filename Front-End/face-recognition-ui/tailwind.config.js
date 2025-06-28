/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./public/**/*.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        'face-primary': '#4f46e5', // custom color
      },
    },
  },
  variants: {
    extend: {},
  },
  plugins: [],
}

