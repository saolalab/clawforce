import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8080",
        changeOrigin: true,
        ws: true,
        configure: (proxy) => {
          proxy.on("proxyRes", (proxyRes) => {
            if (proxyRes.headers["content-type"]?.includes("text/event-stream")) {
              proxyRes.headers["X-Accel-Buffering"] = "no";
              proxyRes.headers["Cache-Control"] = "no-cache";
            }
          });
        },
      },
    },
  },
  build: { outDir: "../clawforce/static" },
});
