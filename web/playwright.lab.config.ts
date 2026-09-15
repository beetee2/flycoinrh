import { defineConfig, devices } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
const evidence = path.resolve(root, process.env.FLYJAM_LAB_EVIDENCE ?? 'artifacts/checks/lab/real-browser');
export default defineConfig({
  testDir: './tests/lab-e2e', fullyParallel: false, workers: 1, retries: 0, timeout: 120_000,
  outputDir: path.join(evidence, 'results'),
  reporter: [['list'], ['json', { outputFile: path.join(evidence, 'report.json') }]],
  use: { baseURL: 'http://127.0.0.1:8766', trace: 'on', screenshot: 'only-on-failure', reducedMotion: 'reduce' },
  projects: [{ name:'chromium',use:{...devices['Desktop Chrome'],viewport:{width:1440,height:1000}} }],
});
