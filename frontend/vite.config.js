import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    allowedHosts: [
      'api-key-checker-tunnel-njnc2f4k.devinapps.com',
      'localhost',
      '127.0.0.1'
    ]
  }
})
