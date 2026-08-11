import { defineConfig } from "@playwright/test";

const browserName = (process.env.PLAYWRIGHT_BROWSER ?? "chromium") as "chromium" | "firefox" | "webkit";

export default defineConfig({
  testDir: "tests",
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:4173",
    browserName,
    channel: browserName === "chromium" ? (process.env.PLAYWRIGHT_CHANNEL ?? "chrome") : undefined,
  },
  webServer: process.env.PLAYWRIGHT_BASE_URL ? undefined : {
    command: "npm run dev -- --host 127.0.0.1 --port 4173",
    port: 4173,
    reuseExistingServer: true,
  },
});
