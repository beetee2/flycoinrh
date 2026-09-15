import { defineConfig, devices } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
// Playwright otherwise writes an accessibility-tree dump after failures, which
// would retain the private inspection panel even with screenshots disabled.
process.env.PLAYWRIGHT_NO_COPY_PROMPT = '1';
const evidence = path.resolve(root, process.env.FLYJAM_LIVE_EVIDENCE ?? 'artifacts/milestones/OBS05/obs-browser');
if (process.env.FLYJAM_OBS_APPROVED !== '/dev/video0' || process.env.FLYJAM_OBS_CONTENT_READY !== 'yes') {
  throw new Error('BLOCKED: selected /dev/video0 identity and displayed-content readiness must be explicitly confirmed before this gate.');
}
const baseURL = process.env.FLYJAM_OBS_URL ?? 'http://127.0.0.1:8767';
if (!/^http:\/\/(127\.0\.0\.1|localhost):\d+$/.test(baseURL)) throw new Error('OBS gate requires an explicit local service URL.');

// The operator-approved local service must already be running with automated
// execution purpose. Never create a device service or retain desktop captures here.
export default defineConfig({
  testDir: './tests/live-gates', testMatch: 'obs.spec.ts', workers: 1, retries: 0,
  timeout: 90_000, outputDir: path.join(evidence, 'results'),
  reporter: [['list'], ['json', { outputFile: path.join(evidence, 'report.json') }]],
  use: { baseURL, trace: 'off', screenshot: 'off', video: 'off',
    launchOptions: { chromiumSandbox: true, ignoreDefaultArgs: ['--enable-unsafe-swiftshader'] } },
  projects: [{ name: 'approved-obs-desktop', use: { ...devices['Desktop Chrome'], headless: true } }],
});
