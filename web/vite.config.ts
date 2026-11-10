import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// In development, API calls go to the Python server (serve.py) on port 8000.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { '/api': 'http://127.0.0.1:8000' },
  },
})
