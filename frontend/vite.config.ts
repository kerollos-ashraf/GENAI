/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig, type ProxyOptions } from "vite";

// The browser only ever talks to its own origin; `/api` is proxied to the FastAPI backend.
// The admin token (if any) is added here, server side, so it never reaches the browser.
// In Docker the same job is done by nginx (nginx/default.conf.template).
const backend = process.env.BACKEND_URL ?? "http://localhost:8000";
const adminToken = process.env.ADMIN_TOKEN;

const proxy: Record<string, ProxyOptions> = {
  "/api": {
    target: backend,
    changeOrigin: true,
    headers: adminToken ? { "X-Admin-Token": adminToken } : undefined,
  },
};

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy },
  preview: { port: 8501, proxy },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    coverage: {
      include: ["src/**/*.{ts,tsx}"],
      exclude: ["src/**/*.test.{ts,tsx}", "src/test/**", "src/main.tsx"],
      // The build fails if coverage drops below these (CI runs `npm run coverage`).
      thresholds: { statements: 85, branches: 75, functions: 85, lines: 85 },
    },
  },
});
