import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
  testDir: './tests/lab-e2e', fullyParallel: false, workers: 1, retries: 0, timeout: 120_000,
  outputDir: '../artifacts/milestones/P00/browser/results',
  reporter: [['list'], ['json', { outputFile: '../artifacts/milestones/P00/browser/report.json' }]],
  use: { baseURL: 'http://127.0.0.1:8766', trace: 'on', screenshot: 'only-on-failure', reducedMotion: 'reduce' },
  projects: [{ name:'chromium',use:{...devices['Desktop Chrome'],viewport:{width:1440,height:1000}} }],
});
