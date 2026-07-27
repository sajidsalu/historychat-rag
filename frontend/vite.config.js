import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Frontend :5173 → FastAPI :8000 (CORS already open on the backend)
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Optional: call /api/... from the frontend and proxy to FastAPI
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
