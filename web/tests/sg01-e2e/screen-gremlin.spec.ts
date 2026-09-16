import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';
import { writeFileSync } from 'node:fs';

const safeReplay = '8d4d624e6f4a4d3f8a9a7dbdc26d3d62';
async function ready(page: Page) {
  await page.goto('/live');
  await expect(page.getByTestId('graphics-state')).toHaveText('Ready');
  await expect(page.getByLabel('Presentation', { exact: true })).toHaveValue('screen-gremlin');
}
async function pose(page: Page) { return JSON.parse((await page.getByTestId('rendered-pose').textContent())!); }

test('original four-background character sheet, composition ratios, same-pose Legacy comparison', async ({ page }, info) => {
  const mutations: string[] = [];
  page.on('request', request => { if (request.method() !== 'GET') mutations.push(new URL(request.url()).pathname); });
  await ready(page);
  await page.getByRole('button', { name: 'Load synthetic preview' }).click();
  await expect(page.getByTestId('preview-data-state')).toHaveText('Loaded');
  await expect.poll(() => pose(page)).not.toBeNull();
  const initial = await pose(page);
  await page.getByText('Illustrative background checks', { exact: true }).click();
  for (const name of ['white', 'black', 'colorful', 'busy']) {
    await page.getByLabel('Safe test background').selectOption(name);
    await expect(page.locator('.screen-backdrop img')).toHaveJSProperty('complete', true);
    await page.locator('.flight-viewport').screenshot({ path: info.outputPath(`character-${name}.png`) });
    expect(await pose(page)).toEqual(initial);
  }
  await page.getByText('Art & composition', { exact: true }).click();
  await page.getByLabel('Caption', { exact: false }).fill('A tiny interruption.');
  await page.getByRole('button', { name: 'Clean view', exact: true }).click();
  await page.locator('.flight-section').screenshot({ path: info.outputPath('landscape-clean.png') });
  await page.getByRole('button', { name: 'Exit clean view' }).click();
  await page.getByLabel('Composition ratio').selectOption('portrait');
  await page.getByRole('button', { name: 'Clean view', exact: true }).click();
  await page.locator('.flight-section').screenshot({ path: info.outputPath('portrait-clean.png') });
  await page.getByRole('button', { name: 'Exit clean view' }).click();
  expect(await pose(page)).toEqual(initial);
  await page.getByLabel('Composition ratio').selectOption('landscape');
  await page.getByLabel('Presentation', { exact: true }).selectOption('legacy');
  await expect(page.getByTestId('graphics-state')).toHaveText('Ready');
  expect(await pose(page)).toEqual(initial);
  await page.locator('.flight-viewport').screenshot({ path: info.outputPath('legacy-same-time.png') });
  await page.getByLabel('Presentation', { exact: true }).selectOption('screen-gremlin');
  expect(await pose(page)).toEqual(initial);
  expect(await page.evaluate(() => ({ local: Object.keys(localStorage), session: Object.keys(sessionStorage) }))).toEqual({ local: [], session: [] });
  expect(mutations).toEqual([]);
});

test('ten-second safe movement, measured display cadence, contact and stopped freeze', async ({ browser }, info) => {
  const context = await browser.newContext({ baseURL: info.project.use.baseURL, viewport: { width: 1280, height: 900 },
    recordVideo: { dir: info.outputPath('safe-video'), size: { width: 1280, height: 900 } } });
  const page = await context.newPage();
  try {
    await page.goto('/live');
    await expect(page.getByTestId('graphics-state')).toHaveText('Ready');
    await page.getByRole('button', { name: 'Load synthetic preview' }).click();
    await page.getByRole('button', { name: 'Clean view', exact: true }).click();
    await page.evaluate(() => {
      const frames: { wall: number; tick: number; contact: boolean; position: number[] }[] = [];
      (window as any).sg01Frames = frames;
      new MutationObserver(() => {
        const value = JSON.parse(document.querySelector('[data-testid="rendered-pose"]')!.textContent!);
        if (value) frames.push({ wall: performance.now(), tick: value.tick, contact: value.ground_contact, position: value.position });
      }).observe(document.querySelector('[data-testid="rendered-pose"]')!, { childList: true, subtree: true, characterData: true });
    });
    await page.getByRole('button', { name: 'Play synthetic preview' }).click();
    await expect.poll(async () => (await pose(page)).ground_contact, { timeout: 6000 }).toBe(true);
    await page.locator('.flight-section').screenshot({ path: info.outputPath('ground-contact.png') });
    await expect.poll(async () => (await pose(page)).tick, { timeout: 12000 }).toBeGreaterThanOrEqual(500);
    await page.getByRole('button', { name: 'Stop', exact: true }).click();
    const stopped = await pose(page);
    await page.waitForTimeout(180);
    expect(await pose(page)).toEqual(stopped);
    await page.locator('.flight-section').screenshot({ path: info.outputPath('stopped-departure.png') });
    const samples = await page.evaluate(() => (window as any).sg01Frames as { wall: number; tick: number; contact: boolean; position: number[] }[]);
    const active = samples.filter((sample, index) => index > 0 && sample.wall - samples[index - 1].wall > 1 && sample.tick < stopped.tick);
    const duration = active.at(-1)!.wall - active[0].wall;
    const intervals = active.slice(1).map((sample, index) => sample.wall - active[index].wall).sort((a, b) => a - b);
    expect(samples.some(sample => sample.contact)).toBe(true);
    expect(samples.every(sample => sample.position[2] >= -2.5)).toBe(true);
    expect(samples.at(-1)!.position[2]).toBeGreaterThan(-2.5);
    const gpu = await page.locator('.flight-canvas canvas').evaluate(canvas => {
      const gl = (canvas as HTMLCanvasElement).getContext('webgl2')!;
      const extension = gl.getExtension('WEBGL_debug_renderer_info');
      return { renderer: extension ? gl.getParameter(extension.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER), vendor: extension ? gl.getParameter(extension.UNMASKED_VENDOR_WEBGL) : gl.getParameter(gl.VENDOR) };
    });
    const renderPerformance = { gpu, browser: await browser.version(), project: info.project.name, source: 'precomputed synthetic control sequence',
      metric: 'DOM-observed completed renderer draws during movement (includes interpolated frames)',
      samples: active.length, duration_ms: duration, display_hz: (active.length - 1) * 1000 / duration,
      frame_interval_median_ms: intervals[Math.floor(intervals.length * .5)], frame_interval_p95_ms: intervals[Math.floor(intervals.length * .95)],
      neural_update_hz: 0, new_model_calls: 0, recording: 'Playwright capture of authorized synthetic artwork only' };
    writeFileSync(info.outputPath('performance.json'), JSON.stringify(renderPerformance, null, 2));
  } finally { await context.close(); }
});

test('selected safe display updates with inspector collapsed and clears on Stop', async ({ page }) => {
  await ready(page);
  await page.getByRole('button', { name: 'Live source', exact: true }).click();
  await page.getByRole('combobox', { name: 'Source', exact: true }).selectOption('fixture-pattern');
  await page.getByRole('button', { name: 'Preview source', exact: true }).click();
  const image = page.getByRole('img', { name: 'Selected source presentation frame' });
  await expect(image).toBeVisible();
  const first = await image.getAttribute('src');
  await expect.poll(() => image.getAttribute('src')).not.toBe(first);
  expect(await page.locator('.session-inspector').getAttribute('open')).toBeNull();
  await expect(page.getByTestId('attempted-calls')).toHaveText('0');
  await page.getByRole('button', { name: 'Stop session', exact: true }).first().click();
  await expect(image).toHaveCount(0);
  await expect(page.locator('.backdrop-empty')).toContainText(/unavailable|stopped/i);
});

test('existing measured safe v1 replay is read-only and its absent original backdrop is visible', async ({ page }) => {
  const mutations: string[] = [];
  page.on('request', request => { if (request.method() !== 'GET') mutations.push(new URL(request.url()).pathname); });
  await ready(page);
  await page.getByRole('button', { name: 'Recorded playback', exact: true }).click();
  await page.getByRole('combobox', { name: 'Recording', exact: true }).selectOption(safeReplay);
  await page.getByRole('button', { name: 'Load recording', exact: true }).click();
  await expect(page.getByTestId('loaded-recording-id')).toHaveText(safeReplay);
  await expect(page.locator('.flight-caption')).toContainText('ORIGINAL COLOR BACKDROP UNAVAILABLE');
  const payload = await (await page.request.get(`/api/live/replays/${safeReplay}`)).json();
  expect(payload.results).toHaveLength(2);
  expect(payload.manifest.source.source_id).toBe('fixture-pattern');
  const tick = Math.min(100, payload.trace.ticks);
  await page.getByLabel('Replay tick').fill(String(tick));
  await expect.poll(async () => (await pose(page)).tick).toBe(tick);
  const recordedPose = await pose(page);
  await page.getByLabel('Presentation', { exact: true }).selectOption('legacy');
  expect(await pose(page)).toEqual(recordedPose);
  expect(recordedPose.schema_version).toBe('obs-flight-1');
  expect(mutations).toEqual([]);
});

test('graphics context loss stops playback and explicit retry recreates one canvas', async ({ page }) => {
  await ready(page);
  await page.getByRole('button', { name: 'Load synthetic preview' }).click();
  await page.getByRole('button', { name: 'Play synthetic preview' }).click();
  await page.locator('canvas').evaluate(canvas => canvas.dispatchEvent(new Event('webglcontextlost', { cancelable: true })));
  await expect(page.getByTestId('graphics-state')).toHaveText('Context lost');
  const frozen = await pose(page);
  await page.waitForTimeout(120);
  expect(await pose(page)).toEqual(frozen);
  await page.getByRole('button', { name: 'Retry graphics', exact: true }).click();
  await expect(page.getByTestId('graphics-state')).toHaveText('Ready');
  await expect(page.locator('.flight-canvas canvas')).toHaveCount(1);
  await expect(page.getByTestId('visible-motion-state')).toContainText('Paused');
});
