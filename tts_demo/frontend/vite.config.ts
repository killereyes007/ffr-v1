import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  base: "/game-assets/",
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: {
      "^/game/(domains|round)": {
        target: process.env.VITE_API_PROXY_TARGET ?? "http://127.0.0.1:7861",
        changeOrigin: true,
      },
      "/training-phrases": {
        target: process.env.VITE_API_PROXY_TARGET ?? "http://127.0.0.1:7861",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
