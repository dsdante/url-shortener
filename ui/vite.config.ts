import { defineConfig } from "vite";

export default defineConfig({
  server: {
    port: 5173,
    // In dev, `npm run dev` proxies /links and /health to the local API.
    proxy: {
      "/links": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
  },
});