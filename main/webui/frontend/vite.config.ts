import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: path.resolve(__dirname, '../static'),
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8190',
        changeOrigin: true,
      },
      '/media': {
        target: 'http://127.0.0.1:8190',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://127.0.0.1:8190',
        ws: true,
      },
    },
  },
})
