import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5174,
    proxy: {
      '/workflows': 'http://localhost:8100',
      '/agents': 'http://localhost:8100',
      '/health': 'http://localhost:8100',
    },
  },
})
