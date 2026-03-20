import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "path";

export default defineConfig({
  base: "/assets/church_management/dist/",
  plugins: [vue()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
    },
  },
  build: {
    outDir: "../public/dist",
    emptyOutDir: true,
    rollupOptions: {
      input: path.resolve(__dirname, "src/main.js"),
      output: {
        entryFileNames: "assets/index.js",
        chunkFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name][extname]",
      },
    },
  },
  server: {
    port: 8081,
    proxy: {
      "/api": {
        target: "http://jbc-pasig.com:8000",
        changeOrigin: true,
      },
    },
  },
});
