import { test, expect } from '@playwright/test';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { deflateSync } from 'node:zlib';
import path from 'node:path';
import { assertDisplayedSnapshot, current, selectLive, startBounded, terminal } from '../live-e2e/journeyHelpers';
import { recordGraphics } from '../live-e2e/graphicsDiagnostics';
import type { ApiSnapshot, NeuralSample } from '../../src/live/contracts';

function inputPng(bytes: number[]) {
  expect(bytes).toHaveLength(256);
  const chunk = (type: string, data: Buffer) => {
    const payload = Buffer.concat([Buffer.from(type), data]);
    let crc = 0xffffffff;
    for (const byte of payload) {
      crc ^= byte;
      for (let bit = 0; bit < 8; bit++) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0);
    }
    const length = Buffer.alloc(4), checksum = Buffer.alloc(4);
    length.writeUInt32BE(data.length); checksum.writeUInt32BE((crc ^ 0xffffffff) >>> 0);
    return Buffer.concat([length, payload, checksum]);
  };
  const header = Buffer.alloc(13); header.writeUInt32BE(16); header.writeUInt32BE(16, 4); header[8] = 8;
  const rows = Buffer.concat(Array.from({ length: 16 }, (_, row) => Buffer.from([0, ...bytes.slice(row * 16, row * 16 + 16)])));
  return Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk('IHDR', header), chunk('IDAT', deflateSync(rows)), chunk('IEND', Buffer.alloc(0))]);
}

test('approved OBS source reaches real neural flight within two automated calls and stops', async ({ page, browser }, info) => {
  const root = path.resolve('..');
  const count = () => readFileSync(path.join(root, 'artifacts/live/validation/attempts.jsonl'), 'utf8').trim().split('\n').length;
  const before = count();
  const graphics = await recordGraphics(page, browser, info);
  expect(graphics.flightAttributes.available).toBe(true);
  try {
    await selectLive(page, 'v4l2-video0');
    expect((await (await page.request.get('/api/live/config')).json()).execution_purpose).toBe('automated');
    await expect(page.getByLabel('Record this session locally', { exact: true })).not.toBeChecked();
    await expect(page.getByLabel('Record this session locally', { exact: true })).toBeDisabled();
    await page.getByRole('button', { name: 'Preview source', exact: true }).click();
    await expect.poll(async () => (await current(page))?.status.state).toBe('previewing');
    await expect(page.getByTestId('source-preview-id')).toContainText('v4l2-video0');
    await expect.poll(async () => JSON.parse((await page.getByTestId('source-preview-bytes').textContent())!).length).toBe(256);
    expect((await current(page))?.status.attempted_calls).toBe(0);
    expect(count()).toBe(before);
    await page.getByRole('button', { name: 'Stop session', exact: true }).click();
    expect((await terminal(page)).status.state).toBe('stopped');
    await startBounded(page, 2, false);
    const inputs = new Map<number, NeuralSample>();
    let final: ApiSnapshot | null = null;
    await expect.poll(async () => {
      final = await current(page);
      if (final?.last_inferred) inputs.set(final.last_inferred.step_index, final.last_inferred);
      return final?.status.state;
    }, { timeout: 60_000, intervals: [20] }).toMatch(/^(stopped|failed|source_lost|limit_reached)$/);
    const completed = final! as ApiSnapshot;
    // Exactly the two processed inputs specifically approved by the operator.
    // Exclusive creation prevents replacement of historical approved evidence.
    if (process.env.FLYJAM_OBS_SAVE_INPUTS === '2') {
      expect([...inputs.keys()].sort()).toEqual([0, 1]);
      const destination = path.join(root, 'artifacts/milestones/OBS05/actual-obs/approved-inputs');
      mkdirSync(destination, { recursive: true, mode: 0o700 });
      for (const [step, sample] of inputs) {
        writeFileSync(path.join(destination, `input-${step}.png`), inputPng(sample.observation_u8), { flag: 'wx', mode: 0o600 });
        writeFileSync(path.join(destination, `input-${step}-identity.json`), JSON.stringify({
          frame: sample.frame, response_id: sample.response_id, step_index: step,
        }, null, 2), { flag: 'wx', mode: 0o600 });
      }
    }
    expect(completed.status.state, completed.status.reason ?? '').toBe('limit_reached');
    expect(completed.status.attempted_calls).toBe(2);
    expect(completed.completed_calls).toBe(2);
    expect(completed.rejected_results).toBe(0);
    expect(completed.model_mode).toBe('real');
    expect(completed.last_inferred?.frame.source_id).toBe('v4l2-video0');
    expect(completed.recording_id).toBeNull(); expect(completed.recording_state).toBe('off');
    expect(count() - before).toBe(2);
    await assertDisplayedSnapshot(page, completed);
    // Persist numerical/identity evidence only. No source thumbnail, private
    // screenshot, recording, browser trace, or raw OBS desktop frame is saved.
    await info.attach('approved OBS numeric identity evidence', { body: JSON.stringify({
      status: completed.status, model_mode: completed.model_mode, model_hz: completed.model_hz,
      frame: completed.last_inferred!.frame, motor_rates_hz: completed.last_inferred!.motor_rates_hz,
      flight: completed.flight, recording_state: completed.recording_state, automated_attempts_added: count() - before,
    }, null, 2), contentType: 'application/json' });
  } finally { await page.getByRole('button', { name: 'Stop session', exact: true }).click({ timeout: 1000 }).catch(() => {}); }
});
