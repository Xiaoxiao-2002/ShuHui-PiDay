import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

const productionBase = "/ShuHui-PiDay/";

export default defineConfig(({ command }) => ({
  base: command === "serve" ? "/" : productionBase,
  plugins: [
    react(),
    VitePWA({
      registerType: "prompt",
      includeAssets: ["icons/icon-192.png", "icons/icon-512.png", "qr-entry.svg"],
      manifest: {
        name: "πDay - 特色数回",
        short_name: "特色数回",
        description: "πDay 特色数回现场挑战",
        lang: "zh-CN",
        start_url: productionBase,
        scope: productionBase,
        display: "standalone",
        orientation: "any",
        background_color: "#f5f2e9",
        theme_color: "#132b49",
        icons: [
          { src: "icons/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "icons/icon-512.png", sizes: "512x512", type: "image/png" },
          { src: "icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,json,png,svg,woff2}"],
        cleanupOutdatedCaches: true,
        navigateFallback: "index.html",
      },
      devOptions: { enabled: false },
    }),
  ],
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    include: ["tests/**/*.test.{ts,tsx}"],
    css: true,
  },
}));
