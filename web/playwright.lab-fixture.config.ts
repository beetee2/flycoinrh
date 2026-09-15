import { defineConfig, devices } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
const evidence = path.resolve(root, process.env.FLYJAM_LAB_EVIDENCE ?? 'artifacts/checks/lab/browser');
const port = Number(process.env.FLYJAM_LAB_FIXTURE_PORT ?? '8898');
if (!Number.isInteger(port) || port < 1024 || port > 65535) throw new Error('Invalid lab fixture port');
const baseURL = `http://127.0.0.1:${port}`;

export default defineConfig({
  testDir: './tests/lab-fixture-e2e', workers: 1, retries: 0, timeout: 20_000,
  outputDir: path.join(evidence, 'results'),
  reporter: [['list'], ['json', { outputFile: path.join(evidence, 'report.json') }]],
  use: { baseURL, trace: 'off', screenshot: 'on',
    launchOptions: { chromiumSandbox: true }, reducedMotion: 'reduce' },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'mobile', use: { ...devices['Pixel 7'] } },
  ],
  webServer: {
    command: `.venv/bin/python -m tests.lab.browser_fixture_server --port ${port}`,
    cwd: root, url: `${baseURL}/health/live`, reuseExistingServer: false, timeout: 20_000,
  },
});
