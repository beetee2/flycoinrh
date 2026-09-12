import { defineConfig, devices } from '@playwright/test';

const evidence = process.env.FLYTRAP_EVIDENCE ?? 'artifacts/milestones/01';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 20_000,
  outputDir: `../${evidence}/browser/results`,
  reporter: [['list'], ['json', { outputFile: `../${evidence}/browser/report.json` }]],
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'on',
    screenshot: 'on',
    reducedMotion: 'reduce',
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile', use: { ...devices['Pixel 7'] } },
  ],
  webServer: [
    {
      command: 'cd .. && .venv/bin/python -m flytrap.cli serve --profile fixture --data-root artifacts/e2e/data --artifact-root artifacts/e2e/runs --port 8765',
      url: 'http://127.0.0.1:8765/health/live',
      reuseExistingServer: false,
      timeout: 20_000,
    },
    { command: 'npm run dev', url: 'http://127.0.0.1:5173', reuseExistingServer: false, timeout: 20_000 },
  ],
});
