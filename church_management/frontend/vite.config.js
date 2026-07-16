import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "path";

// Per-build salt in ALL emitted filenames — entry included. The entry must
// never be referenced under two URLs: lazy chunks import it as a plain
// "./index-<salt>.js", so if the HTML added a ?v= query the browser would
// treat them as two separate modules (double app mount, and the query-less
// copy can be a poisoned year-long cache entry from an older build). Salted
// names make every deploy a fresh URL with no query strings anywhere; the
// www controllers read the real filenames from .vite/manifest.json.
const buildId = Date.now().toString(36);

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
    manifest: true,
    rollupOptions: {
      input: path.resolve(__dirname, "src/main.js"),
      output: {
        entryFileNames: `assets/index-${buildId}.js`,
        chunkFileNames: `assets/[name]-${buildId}.js`,
        assetFileNames: `assets/[name]-${buildId}[extname]`,
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
