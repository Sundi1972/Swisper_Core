import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    allowedHosts: [
      'api-key-checker-tunnel-njnc2f4k.devinapps.com',
      'code-checker-app-tunnel-2j7t5vs0.devinapps.com',
      'localhost',
      '127.0.0.1'
    ]
  },
  define: {
    __API_BASE_URL__: JSON.stringify(process.env.VITE_API_BASE_URL || 'http://localhost:8001')
  }
})
