import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    host: true,

    // ✅ Proxy para desarrollo: /api/* -> http://localhost:8000/*
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        secure: false,
        // Quita el prefijo /api antes de enviar a FastAPI
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
