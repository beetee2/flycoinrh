import { defineConfig, devices } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
const evidence = path.resolve(root, process.env.FLYJAM_LIVE_EVIDENCE ?? 'artifacts/milestones/OBS00/browser');

// Build first with npm run build. The real local idle service serves those assets.
export default defineConfig({
  testDir: './tests/live-e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 20_000,
  outputDir: path.join(evidence, 'results'),
  reporter: [['list'], ['json', { outputFile: path.join(evidence, 'report.json') }]],
  use: {
    baseURL: 'http://127.0.0.1:8876',
    trace: 'off',
    screenshot: 'on',
    reducedMotion: 'reduce',
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile', use: { ...devices['Pixel 7'] } },
  ],
  webServer: {
    command: '.venv/bin/python -m flytrap.live serve --port 8876',
    cwd: root,
    url: 'http://127.0.0.1:8876/health/live',
    reuseExistingServer: false,
    timeout: 20_000,
  },
});
