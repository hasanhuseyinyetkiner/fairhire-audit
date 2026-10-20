import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 120_000,
  expect: { timeout: 30_000 },
  fullyParallel: false,
  use: {
    baseURL: "http://127.0.0.1:5104",
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 2,
    trace: "off",
  },
  webServer: [
    {
      command: "uv run python -m app",
      cwd: "..",
      url: "http://127.0.0.1:8104/ready",
      reuseExistingServer: false,
      timeout: 180_000,
      env: {
        FAIRHIRE_APP_ENV: "demo",
        FAIRHIRE_SEED_DEMO: "true",
        FAIRHIRE_BIND_HOST: "127.0.0.1",
        FAIRHIRE_PORT: "8104",
        FAIRHIRE_ALLOW_NETWORK_BIND: "false",
        FAIRHIRE_DATABASE_URL: "sqlite:///./data/e2e.db",
        FAIRHIRE_BOOTSTRAP_ITERATIONS: "200",
      },
    },
    {
      command: "pnpm exec vite --host 127.0.0.1 --port 5104 --strictPort",
      url: "http://127.0.0.1:5104",
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
