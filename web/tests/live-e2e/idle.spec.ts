import { test, expect, type Locator } from '@playwright/test';
import { attachErrors, collectErrors, recordGraphics } from './graphicsDiagnostics';

async function renderedPixels(canvas: Locator) {
  // Fix the scroll origin: locator screenshots otherwise clip fractional CSS
  // coordinates differently after controls auto-scroll into view.
  await canvas.evaluate(element => window.scrollTo(0, Math.floor(element.getBoundingClientRect().top + window.scrollY)));
  return canvas.screenshot({ scale: 'css' });
}

// Actual local HTTP, Python fixed-step synthetic controls, and locally bundled WebGL.
// These checks never open a capture source, record a session, or invoke the model.
test('explicit synthetic flight plays, freezes, resets, and reloads idle', async ({ page, browser }, testInfo) => {
  const errors = collectErrors(page);
  try {
  const graphics = await recordGraphics(page, browser, testInfo);
  expect(graphics.minimal.available, 'standalone minimal WebGL2 context').toBe(true);
  expect(graphics.flightAttributes.available, 'standalone context with Flyjam attributes').toBe(true);
  const requests: { path: string; method: string }[] = [];
  const unexpectedOrigins: string[] = [];
  page.on('request', request => {
    const url = new URL(request.url());
    if (url.origin !== 'http://127.0.0.1:8876') unexpectedOrigins.push(url.origin);
    requests.push({ path: url.pathname, method: request.method() });
  });
  await page.goto('/live');
  await expect(page.getByTestId('session-status')).toHaveText(/^Idle · local service available$|^Existing session · .*this tab does not own capture\.$/);
  await expect(page.getByText('SYNTHETIC CONTROL REPLAY')).toBeVisible();
  await expect(page.getByTestId('flight-canvas').locator('canvas')).toHaveCount(1);
  await expect(page.getByTestId('graphics-state')).toHaveText('Ready');
  const canvas = page.getByTestId('flight-canvas').locator('canvas');
  await expect(canvas).toBeVisible();
  const licenseHref = await page.getByRole('link', { name: 'three.js (MIT)' }).getAttribute('href');
  expect(licenseHref).toMatch(/^\/assets\/three-LICENSE-.*\.txt$/);
  const license = await page.request.get(licenseHref!);
  expect(license.status()).toBe(200);
  expect(await license.text()).toContain('The MIT License');
  await expect(page.getByRole('button', { name: 'Play synthetic preview' })).toBeDisabled();
  expect(requests.every(request => request.method === 'GET')).toBe(true);
  expect(requests.some(request => request.path === '/api/live/sessions')).toBe(false);

  await page.getByRole('button', { name: 'Load synthetic preview' }).click();
  await expect(page.getByTestId('preview-state')).toHaveText('Loaded · idle');
  await expect(page.getByTestId('flight-tick')).toHaveText('0');
  const initial = await page.getByTestId('flight-position').textContent();
  const initialPixels = await renderedPixels(canvas);
  await testInfo.attach('rendered-initial-pose', { body: initialPixels, contentType: 'image/png' });
  await page.waitForTimeout(150);
  await expect(page.getByTestId('flight-position')).toHaveText(initial!);
  await page.getByRole('button', { name: 'Play synthetic preview' }).click();
  await expect.poll(async () => Number(await page.getByTestId('flight-tick').textContent())).toBeGreaterThan(55);
  await page.getByRole('button', { name: 'Pause', exact: true }).click();
  await expect(page.getByTestId('preview-state')).toHaveText('Paused · frozen');
  const pausedPosition = await page.getByTestId('flight-position').textContent();
  const pausedTick = await page.getByTestId('flight-tick').textContent();
  expect(pausedPosition).not.toBe(initial);
  await page.waitForTimeout(250);
  await expect(page.getByTestId('flight-position')).toHaveText(pausedPosition!);
  await expect(page.getByTestId('flight-tick')).toHaveText(pausedTick!);
  const pausedPixels = await renderedPixels(canvas);
  expect(pausedPixels.equals(initialPixels), 'visible rendered scene advances with the saved poses').toBe(false);
  await testInfo.attach('rendered-paused-pose', { body: pausedPixels, contentType: 'image/png' });
  expect((await renderedPixels(canvas)).equals(pausedPixels), 'Pause freezes rendered pixels').toBe(true);
  const screenshot = testInfo.outputPath(`synthetic-fly-${testInfo.project.name}.png`);
  await page.screenshot({ path: screenshot, fullPage: true });
  await testInfo.attach('synthetic flight preview', { path: screenshot, contentType: 'image/png' });
  const stageScreenshot = testInfo.outputPath(`synthetic-stage-${testInfo.project.name}.png`);
  await page.getByTestId('flight-canvas').screenshot({ path: stageScreenshot });
  await testInfo.attach('original procedural fly', { path: stageScreenshot, contentType: 'image/png' });
  await page.getByRole('button', { name: 'Play synthetic preview' }).click();
  await expect.poll(async () => Number(await page.getByTestId('flight-tick').textContent())).toBeGreaterThan(Number(pausedTick) + 10);
  await page.getByRole('button', { name: 'Stop', exact: true }).click();
  const stopped = await page.getByTestId('flight-position').textContent();
  const stoppedPixels = await renderedPixels(canvas);
  await page.waitForTimeout(250);
  await expect(page.getByTestId('flight-position')).toHaveText(stopped!);
  await expect(page.getByTestId('preview-state')).toHaveText('Stopped · frozen');
  expect((await renderedPixels(canvas)).equals(stoppedPixels), 'Stop freezes rendered pixels').toBe(true);
  await page.getByRole('button', { name: 'Reset preview' }).click();
  await expect(page.getByTestId('flight-tick')).toHaveText('0');
  await expect(page.getByTestId('flight-position')).toHaveText(initial!);
  const resetPixels = await renderedPixels(canvas);
  await testInfo.attach('rendered-reset-pose', { body: resetPixels, contentType: 'image/png' });
  expect(resetPixels.equals(stoppedPixels), 'Reset visibly changes the rendered stopped scene').toBe(false);
  await page.getByRole('button', { name: 'Reset preview' }).click();
  await expect(page.getByTestId('flight-tick')).toHaveText('0');
  await expect(page.getByTestId('flight-position')).toHaveText(initial!);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.reload();
  await expect(page.getByTestId('session-status')).toHaveText(/^Idle · local service available$|^Existing session · .*this tab does not own capture\.$/);
  await expect(page.getByRole('button', { name: 'Play synthetic preview' })).toBeDisabled();
  await expect(page.getByTestId('flight-canvas').locator('canvas')).toHaveCount(1);
  await expect(page.getByTestId('graphics-state')).toHaveText('Ready');
  await testInfo.attach('rendered-reloaded-idle', { body: await renderedPixels(canvas), contentType: 'image/png' });
  await expect(page.getByRole('alert')).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  expect(requests.filter(request => request.path === '/api/live/flight-preview')).toHaveLength(1);
  expect(requests.every(request => request.method === 'GET')).toBe(true);
  expect(unexpectedOrigins).toEqual([]); expect(errors.pageErrors).toEqual([]); expect(errors.consoleErrors).toEqual([]);
  } finally { await attachErrors(testInfo, errors); }
});

test('unavailable WebGL shows a usable honest fallback', async ({ page }, testInfo) => {
  const errors = collectErrors(page);
  try {
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function(this: HTMLCanvasElement, kind: string, ...args: unknown[]) {
      if (kind.startsWith('webgl')) return null;
      return (original as any).apply(this, [kind, ...args]);
    } as typeof original;
  });
  await page.goto('/live');
  await expect(page.getByText(/3D view unavailable/)).toBeVisible();
  await expect(page.getByTestId('graphics-state')).toHaveText('Context creation failed');
  await page.getByRole('button', { name: 'Load synthetic preview' }).click();
  await expect(page.getByTestId('preview-state')).toHaveText('Loaded · idle');
  await expect(page.getByRole('button', { name: 'Play synthetic preview' })).toBeDisabled();
  await expect(page.getByTestId('flight-tick')).toHaveText('0');
  await expect(page.getByTestId('preview-data-state')).toHaveText('Loaded');
  await expect(page.getByTestId('graphics-details')).toContainText(/WebGL2|context/i);
  await expect(page.getByTestId('flight-canvas').locator('canvas')).toHaveCount(0);
  expect(errors.pageErrors).toEqual([]); expect(errors.consoleErrors).toEqual([]);
  } finally { await attachErrors(testInfo, errors, true); }
});

test('creation details survive a failed retry and explicit successful retry stays idle', async ({ page }, testInfo) => {
  const errors = collectErrors(page);
  try {
  await page.addInitScript(() => {
    const state = window as unknown as { graphicsBlocked: boolean; graphicsAttempts: number };
    state.graphicsBlocked = true; state.graphicsAttempts = 0;
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function(this: HTMLCanvasElement, kind: string, ...args: unknown[]) {
      if (kind === 'webgl2') {
        state.graphicsAttempts++;
        if (state.graphicsBlocked) {
          this.dispatchEvent(new WebGLContextEvent('webglcontextcreationerror', { statusMessage: 'Forced diagnostic: BindToCurrentSequence failed' }));
          return null;
        }
      }
      return (original as any).apply(this, [kind, ...args]);
    } as typeof original;
  });
  await page.goto('/live');
  await expect(page.getByTestId('graphics-details')).toContainText('BindToCurrentSequence failed');
  await page.getByRole('button', { name: 'Load synthetic preview' }).click();
  await expect(page.getByTestId('preview-data-state')).toHaveText('Loaded');
  const initialAttempts = await page.evaluate(() => (window as unknown as { graphicsAttempts: number }).graphicsAttempts);
  await page.getByRole('button', { name: 'Retry graphics', exact: true }).click();
  await expect(page.getByTestId('graphics-state')).toHaveText('Context creation failed');
  await expect(page.getByTestId('graphics-details')).toContainText('BindToCurrentSequence failed');
  await expect(page.getByRole('button', { name: 'Play synthetic preview' })).toBeDisabled();
  expect(await page.evaluate(() => (window as unknown as { graphicsAttempts: number }).graphicsAttempts)).toBe(initialAttempts + 1);
  await page.waitForTimeout(200);
  expect(await page.evaluate(() => (window as unknown as { graphicsAttempts: number }).graphicsAttempts), 'no automatic failed initialization loop').toBe(initialAttempts + 1);
  await expect(page.getByTestId('flight-canvas').locator('canvas')).toHaveCount(0);
  await page.evaluate(() => { (window as unknown as { graphicsBlocked: boolean }).graphicsBlocked = false; });
  await page.getByRole('button', { name: 'Retry graphics', exact: true }).click();
  await expect(page.getByTestId('graphics-state')).toHaveText('Ready');
  await expect(page.getByTestId('flight-canvas').locator('canvas')).toHaveCount(1);
  await expect(page.getByTestId('preview-state')).toHaveText('Paused · graphics restored');
  await expect(page.getByTestId('flight-tick')).toHaveText('0');
  await expect(page.getByRole('button', { name: 'Play synthetic preview' })).toBeEnabled();
  expect(errors.pageErrors).toEqual([]); expect(errors.consoleErrors).toEqual([]);
  } finally { await attachErrors(testInfo, errors, true); }
});

test('context loss freezes playback and explicit recreation leaves one idle renderer', async ({ page }, testInfo) => {
  const errors = collectErrors(page);
  try {
  await page.goto('/live');
  await page.getByRole('button', { name: 'Load synthetic preview' }).click();
  await page.getByRole('button', { name: 'Play synthetic preview' }).click();
  await expect.poll(async () => Number(await page.getByTestId('flight-tick').textContent())).toBeGreaterThan(10);
  const lost = await page.getByTestId('flight-canvas').locator('canvas').evaluate(canvas => {
    const extension = (canvas as HTMLCanvasElement).getContext('webgl2')?.getExtension('WEBGL_lose_context');
    if (!extension) return false;
    extension.loseContext(); return true;
  });
  expect(lost, 'browser exposes WEBGL_lose_context for a real context loss').toBe(true);
  await expect(page.getByTestId('graphics-state')).toHaveText('Context lost');
  await expect(page.getByRole('button', { name: 'Play synthetic preview' })).toBeDisabled();
  const frozenTick = await page.getByTestId('flight-tick').textContent();
  await page.waitForTimeout(200);
  await expect(page.getByTestId('flight-tick')).toHaveText(frozenTick!);
  await page.getByRole('button', { name: 'Retry graphics', exact: true }).click();
  await expect(page.getByTestId('graphics-state')).toHaveText('Ready');
  await expect(page.getByTestId('flight-canvas').locator('canvas')).toHaveCount(1);
  await expect(page.getByRole('button', { name: 'Pause', exact: true })).toBeDisabled();
  await page.waitForTimeout(200);
  await expect(page.getByTestId('flight-tick')).toHaveText(frozenTick!);
  await page.reload();
  await expect(page.getByTestId('graphics-state')).toHaveText('Ready');
  await expect(page.getByTestId('flight-canvas').locator('canvas')).toHaveCount(1);
  await expect(page.getByRole('button', { name: 'Play synthetic preview' })).toBeDisabled();
  expect(errors.pageErrors).toEqual([]); expect(errors.consoleErrors).toEqual([]);
  } finally { await attachErrors(testInfo, errors, true); }
});
