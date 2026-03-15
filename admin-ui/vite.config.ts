import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/krsna/',
  server: {
    port: 5173,
    proxy: {
      '/admin': 'http://localhost:8000',
      '/webhook': 'http://localhost:8000',
    }
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  }
})
