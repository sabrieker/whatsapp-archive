/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        whatsapp: {
          green: '#25D366',
          teal: '#128C7E',
          dark: '#075E54',
          light: '#DCF8C6',
          bg: '#ECE5DD',
          panel: '#EDEDED',
          hover: '#F5F5F5',
          incoming: '#FFFFFF',
          outgoing: '#DCF8C6',
        },
      },
    },
  },
  plugins: [],
}
