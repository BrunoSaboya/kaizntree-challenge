import react from "@vitejs/plugin-react";
import path from "path";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        // API_PROXY_TARGET is server-side only (no VITE_ prefix → never bundled into the browser).
        // VITE_API_URL fallback keeps production Vercel builds working if someone sets that instead.
        target: process.env.API_PROXY_TARGET || process.env.VITE_API_URL || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
