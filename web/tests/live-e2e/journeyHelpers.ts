import { expect, type Page, type TestInfo } from '@playwright/test';
import { createHash } from 'node:crypto';
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import Ajv2020 from 'ajv/dist/2020.js';
import type { ApiSnapshot, ContractName, LiveContracts } from '../../src/live/contracts';

const schemas = JSON.parse(readFileSync(new URL('../../src/live/generated/schemas.json', import.meta.url), 'utf8'));
const ajv = new Ajv2020({ strict: false, allErrors: true });
const validators = new Map<ContractName, ReturnType<typeof ajv.compile>>();
export function parseLiveContract<K extends ContractName>(name: K, value: unknown): LiveContracts[K] {
  let validate = validators.get(name);
  if (!validate) { validate = ajv.compile(schemas[name]); validators.set(name, validate); }
  expect(validate(value), `actual HTTP response matches ${name}: ${JSON.stringify(validate.errors)}`).toBe(true);
  return value as LiveContracts[K];
}

export function ledgers(root: string): Record<string, string> {
  const result: Record<string, string> = {};
  const visit = (directory: string) => {
    if (!existsSync(directory)) return;
    for (const item of readdirSync(directory, { withFileTypes: true })) {
      const location = path.join(directory, item.name);
      if (item.isDirectory()) visit(location);
      else if (/^attempts\.(jsonl|state\.json)$/.test(item.name)) {
        result[path.relative(root, location)] = createHash('sha256').update(readFileSync(location)).digest('hex');
      }
    }
  };
  visit(path.join(root, 'artifacts/live'));
  visit(path.join(root, 'artifacts/milestones/P00'));
  return result;
}

export async function current(page: Page): Promise<ApiSnapshot | null> {
  const response = await page.request.get('/api/live/status');
  expect(response.ok()).toBe(true);
  return parseLiveContract('ServiceStatus', await response.json()).current;
}

export async function selectLive(page: Page, source = 'fixture-pattern') {
  await page.goto('/live');
  await expect(page.getByTestId('graphics-state')).toHaveText('Ready');
  await page.getByRole('button', { name: 'Live source', exact: true }).click();
  await page.getByRole('combobox', { name: 'Source', exact: true }).selectOption(source);
  await page.getByText('Session details & input inspector', { exact: true }).click();
  await page.getByLabel('Inspect input', { exact: true }).check();
}

export async function startBounded(page: Page, calls: number, recording = false) {
  await page.getByLabel('Maximum model calls', { exact: true }).fill(String(calls));
  await page.getByLabel('Session duration (seconds)', { exact: true }).fill('30');
  await page.getByLabel('Seed', { exact: true }).fill('20260915');
  if (recording) await page.getByLabel('Record this session locally', { exact: true }).check();
  const response = page.waitForResponse(reply => new URL(reply.url()).pathname === '/api/live/sessions' && reply.request().method() === 'POST');
  await page.getByRole('button', { name: 'Start live flight', exact: true }).click();
  const reply = await response;
  expect(reply.ok(), await reply.text()).toBe(true);
  return parseLiveContract('ApiSnapshot', await reply.json());
}

export async function terminal(page: Page, timeout = 30_000): Promise<ApiSnapshot> {
  let latest: ApiSnapshot | null = null;
  await expect.poll(async () => {
    latest = await current(page);
    return latest?.recording_state === 'partial' ? 'finalizing-recording' : latest?.status.state;
  }, { timeout }).toMatch(/^(stopped|failed|source_lost|limit_reached)$/);
  return latest!;
}

export async function assertDisplayedSnapshot(page: Page, snapshot: ApiSnapshot) {
  const sample = snapshot.last_inferred;
  expect(sample, 'a completed sample is required').not.toBeNull();
  await expect.poll(async () => JSON.parse((await page.getByTestId('inferred-input-bytes').textContent())!)).toEqual(sample!.observation_u8);
  const squares = page.getByRole('img', { name: 'Exact input used for displayed neural response', exact: true }).locator('rect');
  await expect(squares).toHaveCount(256);
  expect(await squares.evaluateAll(elements => elements.map(element => ({
    x: Number(element.getAttribute('x')), y: Number(element.getAttribute('y')), fill: element.getAttribute('fill'),
  })))).toEqual(sample!.observation_u8.map((value, index) => ({ x: index % 16, y: Math.floor(index / 16), fill: `rgb(${value},${value},${value})` })));
  await expect(page.getByTestId('inferred-input-id')).toContainText(sample!.frame.source_id);
  await expect(page.getByTestId('inferred-input-id')).toContainText(String(sample!.frame.sequence));
  await expect.poll(async () => JSON.parse((await page.getByTestId('neural-values').textContent())!)).toEqual(sample!.motor_rates_hz);
  await expect.poll(async () => JSON.parse((await page.getByTestId('authoritative-pose').textContent())!)).toEqual(snapshot.flight);
  await expect.poll(async () => JSON.parse((await page.getByTestId('rendered-pose').textContent())!)).toEqual(snapshot.flight);
  expect(snapshot.flight?.session_id).toBe(sample!.frame.session_id);
}

export function assertFixtureOracle(snapshot: Pick<ApiSnapshot, 'last_inferred'>) {
  const sample = snapshot.last_inferred!;
  const result = spawnSync(path.resolve('../.venv/bin/python'), ['-m', 'tests.live.browser_oracle'], {
    cwd: path.resolve('..'), encoding: 'utf8', input: JSON.stringify(sample.frame),
  });
  expect(result.status, result.stderr).toBe(0);
  expect(sample.observation_u8, 'independent nearest-center RGB/grayscale oracle').toEqual(JSON.parse(result.stdout));
}

type RecordingExpectation = Pick<ApiSnapshot, 'recording_state' | 'recording_id' | 'last_inferred' | 'flight'> & {
  status: Pick<ApiSnapshot['status'], 'session_id' | 'attempted_calls'>;
};
export async function replayRecorded(page: Page, snapshot: RecordingExpectation, root: string, info: TestInfo, idleService = false) {
  expect(snapshot.recording_state).toBe('complete');
  expect(snapshot.recording_id).not.toBeNull();
  const before = ledgers(root);
  const mutationRequests: string[] = [];
  const watch = (request: { method(): string; url(): string }) => { if (request.method() !== 'GET') mutationRequests.push(request.url()); };
  page.on('request', watch);
  await page.getByRole('button', { name: 'Recorded playback', exact: true }).click();
  await page.getByRole('button', { name: 'Refresh recordings', exact: true }).click();
  await page.getByRole('combobox', { name: 'Recording', exact: true }).selectOption(snapshot.recording_id!);
  await page.getByRole('button', { name: 'Load recording', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Play recording', exact: true })).toBeEnabled();
  const response = await page.request.get(`/api/live/replays/${snapshot.recording_id}`);
  expect(response.ok()).toBe(true);
  const replay = parseLiveContract('ReplayPayload', await response.json());
  expect(replay.manifest.session_id).toBe(snapshot.status.session_id);
  expect(replay.samples.at(-1)).toEqual(snapshot.last_inferred);
  for (const sample of replay.samples) assertFixtureOracle({ last_inferred: sample });
  expect(replay.final.snapshot).toEqual(snapshot.flight);
  await page.getByRole('button', { name: 'Play recording', exact: true }).click();
  await page.getByRole('button', { name: 'Pause recording', exact: true }).click();
  const slider = page.getByRole('slider', { name: 'Replay tick', exact: true });
  await slider.focus();
  await slider.press('End');
  await expect.poll(async () => JSON.parse((await page.getByTestId('rendered-pose').textContent())!)).toEqual(replay.final.snapshot);
  const downloadEvent = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download recording', exact: true }).click();
  const download = await downloadEvent;
  const downloadPath = info.outputPath('safe-recorded-evidence.json');
  await download.saveAs(downloadPath);
  expect(parseLiveContract('ReplayPayload', JSON.parse(readFileSync(downloadPath, 'utf8')))).toEqual(replay);
  expect(ledgers(root), 'replay leaves every model-call ledger byte-identical').toEqual(before);
  expect(mutationRequests, 'replay performs passive requests only').toEqual([]);
  if (idleService) expect(await current(page), 'replay must not create a capture or model session').toBeNull();
  else expect((await current(page))?.status.attempted_calls).toBe(snapshot.status.attempted_calls);
  page.off('request', watch);
}
