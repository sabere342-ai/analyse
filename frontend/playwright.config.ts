import { defineConfig } from "@playwright/test";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
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
      ...(process.env.MADRID_BROWSER
        ? { executablePath: process.env.MADRID_BROWSER }
        : {}),
    },
    trace: "retain-on-failure",
  },
  webServer: {
    command: `"${resolve("..", ".venv", process.platform === "win32" ? "Scripts/python.exe" : "bin/python")}" -m uvicorn madrid.app:create_app --factory --app-dir .. --host 127.0.0.1 --port 8123`,
    url: "http://127.0.0.1:8123/api/health",
    reuseExistingServer: false,
    env: {
      MADRID_DATA_DIR: resolve(
        tmpdir(),
        `madrid-e2e-${process.pid}-${Date.now()}`,
      ),
      MADRID_DATABASE_URL: "",
      MADRID_REQUIRE_CLOUD_DATABASE: "0",
      XDG_CACHE_HOME: resolve("..", ".cache"),
    },
    timeout: 30000,
  },
});
