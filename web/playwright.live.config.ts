import { defineConfig, devices } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { existsSync } from 'node:fs';

const root = fileURLToPath(new URL('..', import.meta.url));
const evidence = path.resolve(root, process.env.FLYJAM_LIVE_EVIDENCE ?? 'artifacts/milestones/OBS05/browser');
const compatibilityBrowser = process.env.FLYJAM_COMPAT_BROWSER;
if (compatibilityBrowser && (!path.isAbsolute(compatibilityBrowser) || !existsSync(compatibilityBrowser))) {
  throw new Error('FLYJAM_COMPAT_BROWSER must name an existing absolute browser executable.');
}

// Build first with npm run build. Actual service/processes use only safe synthetic inputs.
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
    launchOptions: { chromiumSandbox: true, ignoreDefaultArgs: ['--enable-unsafe-swiftshader'] },
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'], headless: true } },
    { name: 'mobile', use: { ...devices['Pixel 7'], headless: true } },
    // Opt in with an exact Chromium-family binary. Playwright creates and removes
    // its own temporary profile; this never connects to a personal browser.
    // Use the host's normal graphics decisions: no GPU/blocklist/security flags.
    ...(compatibilityBrowser ? [{ name: 'installed-headed', use: {
      viewport: devices['Desktop Chrome'].viewport, headless: false,
      launchOptions: { executablePath: compatibilityBrowser, chromiumSandbox: true, ignoreDefaultArgs: ['--enable-unsafe-swiftshader'] },
    } }] : []),
  ],
  webServer: {
    command: '.venv/bin/python -m tests.live.browser_server --port 8876 --state artifacts/live/browser-fixture',
    cwd: root,
    url: 'http://127.0.0.1:8876/health/live',
    reuseExistingServer: false,
    timeout: 20_000,
  },
});
