import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Frontend for DIRECTIVES (planner). Built to static files the Pi (FastAPI)
// serves directly. In dev, /api is proxied to the local REST API (port 8000)
// so the app uses same-origin relative URLs in both dev and production.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
