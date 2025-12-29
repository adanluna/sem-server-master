import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  server: {
    port: 3000,      // el puerto que quieras
    host: true,       // opcional, útil si accedes desde otra IP
  },
  plugins: [vue()],
})
