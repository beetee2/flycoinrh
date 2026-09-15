import { test, expect } from '@playwright/test';
import path from 'node:path';
import { readFileSync } from 'node:fs';
import { assertDisplayedSnapshot, assertFixtureOracle, replayRecorded, selectLive, startBounded, terminal } from '../live-e2e/journeyHelpers';
import { attachErrors, collectErrors, recordGraphics } from '../live-e2e/graphicsDiagnostics';

test('actual CPU baseline: two automated safe-input calls, authoritative browser flight and passive replay', async ({ page, browser }, info) => {
  const root = path.resolve('..');
  const count = () => readFileSync(path.join(root, 'artifacts/live/validation/attempts.jsonl'), 'utf8').trim().split('\n').length;
  const before = count();
  const errors = collectErrors(page);
  try {
    const graphics = await recordGraphics(page, browser, info);
    expect(graphics.flightAttributes.available).toBe(true);
    await selectLive(page);
    expect((await (await page.request.get('/api/live/config')).json()).execution_purpose).toBe('automated');
    const started = await startBounded(page, 2, true);
    const final = await terminal(page, 60_000);
    expect(final.status.session_id).toBe(started.status.session_id);
    expect(final.status.state, final.status.reason ?? '').toBe('limit_reached');
    expect(final.status.attempted_calls).toBe(2);
    expect(final.completed_calls).toBe(2);
    expect(final.rejected_results).toBe(0);
    expect(final.model_mode).toBe('real');
    expect(final.last_inferred?.model_id).toMatch(/^baseline-/);
    expect(count() - before, 'browser-triggered calls count against the automated allowance').toBe(2);
    await assertDisplayedSnapshot(page, final);
    assertFixtureOracle(final);
    await info.attach('safe real-model final snapshot', { body: JSON.stringify(final, null, 2), contentType: 'application/json' });
    const screenshot = info.outputPath('safe-real-model-flight.png');
    await page.screenshot({ path: screenshot, fullPage: true });
    await info.attach('safe real-model browser', { path: screenshot, contentType: 'image/png' });
    await replayRecorded(page, final, root, info);
    expect(count() - before).toBe(2);
    expect(errors.pageErrors).toEqual([]); expect(errors.consoleErrors).toEqual([]);
  } finally {
    await page.getByRole('button', { name: 'Stop session', exact: true }).click({ timeout: 1000 }).catch(() => {});
    await attachErrors(info, errors);
  }
});
