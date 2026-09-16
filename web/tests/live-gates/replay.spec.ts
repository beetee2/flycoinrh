import { test, expect } from '@playwright/test';
import path from 'node:path';
import { current, ledgers, parseLiveContract, replayRecorded } from '../live-e2e/journeyHelpers';
import { collectErrors, attachErrors, recordGraphics } from '../live-e2e/graphicsDiagnostics';

test('existing safe real recording plays, seeks and downloads exactly with zero capture or model calls', async ({ page, browser }, info) => {
  const root = path.resolve('..');
  const before = ledgers(root);
  const recordingId = process.env.FLYJAM_REPLAY_ID!;
  const errors = collectErrors(page);
  const mutations: string[] = [];
  page.on('request', request => { if (request.method() !== 'GET') mutations.push(request.url()); });
  try {
    const graphics = await recordGraphics(page, browser, info);
    expect(graphics.flightAttributes.available).toBe(true);
    expect(await current(page)).toBeNull();
    const reply = await page.request.get(`/api/live/replays/${recordingId}`);
    expect(reply.ok()).toBe(true);
    const payload = parseLiveContract('ReplayPayload', await reply.json());
    expect(payload.manifest.source.source_id).toBe('fixture-pattern');
    expect(payload.manifest.provenance.model_id).toMatch(/^baseline-/);
    expect(payload.results).toHaveLength(2);
    expect(payload.samples).toHaveLength(2);
    expect(payload.results.every(result => result.output.model_mode === 'windowed_reset')).toBe(true);
    await page.goto('/live');
    await expect(page.getByTestId('graphics-state')).toHaveText('Ready');
    await page.getByText('Session details & input inspector', { exact: true }).click();
    await page.getByLabel('Inspect input', { exact: true }).check();
    await replayRecorded(page, { recording_state: 'complete', recording_id: recordingId,
      last_inferred: payload.samples.at(-1)!, flight: payload.final.snapshot,
      status: { session_id: payload.manifest.session_id, attempted_calls: payload.results.length },
    }, root, info, true);
    await expect(page.getByTestId('loaded-recording-id')).toHaveText(recordingId);
    // The call-limit response can finish before its controls survive a flight
    // tick. Replay inspection follows the response actually applied by the
    // recorded trace; the download still preserves both completed responses.
    const applications = payload.trace.events.filter(event => event.controls && event.tick <= payload.final.snapshot.tick);
    const appliedId = applications.at(-1)?.controls?.response_id;
    const displayed = payload.samples.find(sample => sample.response_id === appliedId);
    expect(displayed).toBeDefined();
    await expect(page.getByTestId('inferred-input-id')).toContainText(displayed!.response_id);
    await expect.poll(async () => JSON.parse((await page.getByTestId('neural-values').textContent())!)).toEqual(displayed!.motor_rates_hz);
    await expect.poll(async () => JSON.parse((await page.getByTestId('inferred-input-bytes').textContent())!)).toEqual(displayed!.observation_u8);
    expect(await current(page)).toBeNull();
    expect(ledgers(root)).toEqual(before);
    expect(mutations).toEqual([]);
    expect(errors.pageErrors).toEqual([]); expect(errors.consoleErrors).toEqual([]);
    await info.attach('zero-call replay evidence', { body: JSON.stringify({
      recording_id: recordingId, session_id: payload.manifest.session_id,
      model_id: payload.manifest.provenance.model_id, samples: payload.samples.length,
      ledger_hashes_before: before, ledger_hashes_after: ledgers(root), current: null, mutations,
    }, null, 2), contentType: 'application/json' });
    await page.screenshot({ path: info.outputPath('safe-real-recorded-playback.png'), fullPage: true });
  } finally { await attachErrors(info, errors); }
});
