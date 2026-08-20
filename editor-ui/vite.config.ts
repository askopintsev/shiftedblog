import { fileURLToPath, URL } from "node:url";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const devHost = process.env.VITE_DEV_HOST || "127.0.0.1";
const proxyTarget = process.env.VITE_PROXY_TARGET || "http://localhost:8888";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    host: devHost,
    port: 5173,
    proxy: {
      "/api": {
        target: proxyTarget,
        changeOrigin: false,
      },
      "/media": {
        target: proxyTarget,
        changeOrigin: false,
      },
    },
  },
  preview: {
    host: devHost,
    port: 5173,
  },
  build: {
    outDir: "dist",
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("ckeditor5") || id.includes("@ckeditor")) {
            return "ckeditor";
          }
        },
      },
    },
  },
});
