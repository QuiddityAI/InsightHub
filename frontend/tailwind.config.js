/** @type {import('tailwindcss').Config} */

const defaultTheme = require('tailwindcss/defaultTheme')

export default {
  content: [
    "./*.html",
    "./src/**/*.{js,ts,vue}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter var', ...defaultTheme.fontFamily.sans],
      },
      animation: {
				fade: 'fadeIn .3s ease-in',
			},
      keyframes: {
        fadeIn: {
					from: { opacity: 0 },
					to: { opacity: 1 },
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
}

