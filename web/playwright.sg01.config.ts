import { defineConfig } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { existsSync } from 'node:fs';

const root = fileURLToPath(new URL('..', import.meta.url));
const evidence = path.resolve(root, process.env.FLYJAM_SG01_EVIDENCE ?? 'artifacts/milestones/SG01/browser-local');
const installed = process.env.FLYJAM_COMPAT_BROWSER;
const development = process.env.FLYJAM_SG01_DEV === '1';
if (installed && (!path.isAbsolute(installed) || !existsSync(installed))) throw new Error('Browser must be an existing absolute executable.');

export default defineConfig({
  testDir: './tests/sg01-e2e', workers: 1, retries: 0, timeout: 40_000,
  outputDir: path.join(evidence, 'results'),
  reporter: [['list'], ['json', { outputFile: path.join(evidence, 'report.json') }]],
  use: { baseURL: development ? 'http://127.0.0.1:5174' : 'http://127.0.0.1:8771', viewport: { width: 1440, height: 1080 },
    trace: 'off', screenshot: 'off', video: 'off',
    launchOptions: { chromiumSandbox: true, ignoreDefaultArgs: ['--enable-unsafe-swiftshader'] } },
  projects: [{ name: 'headless', use: { headless: true } }, ...(installed ? [{ name: 'installed-headed', use: {
    headless: false, launchOptions: { executablePath: installed, chromiumSandbox: true, ignoreDefaultArgs: ['--enable-unsafe-swiftshader'] },
  } }] : [])],
  webServer: [
    { command: '.venv/bin/python -m scripts.sg01_preview --port 8771', cwd: root,
      url: 'http://127.0.0.1:8771/health/live', reuseExistingServer: false, timeout: 20_000 },
    ...(development ? [{ command: 'FLYJAM_API_PORT=8771 npm --prefix web run dev -- --port 5174', cwd: root,
      url: 'http://127.0.0.1:5174/live', reuseExistingServer: false, timeout: 20_000 }] : []),
  ],
});
