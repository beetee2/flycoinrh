import { defineConfig } from '@playwright/test';
import path from 'node:path';
import real from './playwright.live-real.config';

if (!/^[0-9a-f]{32}$/.test(process.env.FLYJAM_REPLAY_ID ?? '')) {
  throw new Error('Explicit FLYJAM_REPLAY_ID is required for the passive replay gate.');
}
const evidence = path.resolve('..', process.env.FLYJAM_LIVE_EVIDENCE ?? 'artifacts/milestones/OBS05/real-replay-repair');

// Fresh, idle real service exposes only the deterministic source. This test makes
// no control mutation: it opens one existing recording without starting a session.
export default defineConfig(real, {
  testMatch: 'replay.spec.ts', outputDir: path.join(evidence, 'results'),
  reporter: [['list'], ['json', { outputFile: path.join(evidence, 'report.json') }]],
});
