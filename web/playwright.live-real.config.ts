import { defineConfig, devices } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
const evidence = path.resolve(root, process.env.FLYJAM_LIVE_EVIDENCE ?? 'artifacts/milestones/OBS05/real-browser');

// Explicit, separately invoked two-call gate. No retries or device discovery.
export default defineConfig({
  testDir: './tests/live-gates', testMatch: 'real.spec.ts', workers: 1, retries: 0,
  timeout: 90_000, outputDir: path.join(evidence, 'results'),
  reporter: [['list'], ['json', { outputFile: path.join(evidence, 'report.json') }]],
  use: { baseURL: 'http://127.0.0.1:8877', trace: 'off', screenshot: 'on', video: 'off',
    launchOptions: { chromiumSandbox: true, ignoreDefaultArgs: ['--enable-unsafe-swiftshader'] } },
  projects: [{ name: 'real-desktop', use: { ...devices['Desktop Chrome'], headless: true } }],
  webServer: { command: '.venv/bin/python -m flytrap.live serve --port 8877 --safe-source --execution-purpose automated',
    cwd: root, url: 'http://127.0.0.1:8877/health/live', reuseExistingServer: false, timeout: 20_000 },
});
