import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  fullyParallel: false,
  timeout: 60000,
  use: {
    baseURL: "http://127.0.0.1:8123",
    browserName: "chromium",
    headless: true,
    reducedMotion: "reduce",
    launchOptions: {
      executablePath: process.env.MADRID_BROWSER || "/usr/bin/chromium",
    },
    trace: "retain-on-failure",
  },
  webServer: {
    command:
      "../.venv/bin/uvicorn madrid.app:create_app --factory --app-dir .. --host 127.0.0.1 --port 8123",
    url: "http://127.0.0.1:8123/api/health",
    reuseExistingServer: false,
    env: {
      MADRID_DATA_DIR: `/tmp/madrid-e2e-${process.pid}-${Date.now()}`,
      XDG_CACHE_HOME: "/workspace/.cache",
    },
    timeout: 30000,
  },
});
