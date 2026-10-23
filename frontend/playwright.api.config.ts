import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './tests/api',
  fullyParallel: false,
  workers: 1,
  timeout: 60000,
  use: {
    baseURL: 'http://127.0.0.1:5173',
    ...devices['Desktop Chrome'],
    viewport: { width: 1440, height: 1000 },
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 5173 --strictPort',
      url: 'http://127.0.0.1:5173',
      reuseExistingServer: !process.env.CI,
      timeout: 30000,
    },
    {
      command: '../backend/.venv/bin/uvicorn tests.browser_e2e_app:app --app-dir ../backend --host 127.0.0.1 --port 8000',
      url: 'http://127.0.0.1:8000/api/v1/health/ready',
      reuseExistingServer: !process.env.CI,
      timeout: 60000,
    },
  ],
})
