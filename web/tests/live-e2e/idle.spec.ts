import { test, expect } from '@playwright/test';

// Actual local HTTP, Python fixed-step synthetic controls, and locally bundled WebGL.
// These checks never open a capture source, record a session, or invoke the model.
test('explicit synthetic flight plays, freezes, resets, and reloads idle', async ({ page }, testInfo) => {
  const pageErrors: string[] = [];
  const requests: { path: string; method: string }[] = [];
  const unexpectedOrigins: string[] = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  page.on('request', request => {
    const url = new URL(request.url());
    if (url.origin !== 'http://127.0.0.1:8876') unexpectedOrigins.push(url.origin);
    requests.push({ path: url.pathname, method: request.method() });
  });
  await page.goto('/live');
  await expect(page.getByText('Idle · local service available')).toBeVisible();
  await expect(page.getByText('SYNTHETIC CONTROL REPLAY')).toBeVisible();
  await expect(page.getByTestId('flight-canvas').locator('canvas')).toHaveCount(1);
  const licenseHref = await page.getByRole('link', { name: 'three.js (MIT)' }).getAttribute('href');
  expect(licenseHref).toMatch(/^\/assets\/three-LICENSE-.*\.txt$/);
  const license = await page.request.get(licenseHref!);
  expect(license.status()).toBe(200);
  expect(await license.text()).toContain('The MIT License');
  await expect(page.getByRole('button', { name: 'Play synthetic preview' })).toBeDisabled();
  expect(requests.filter(request => request.path.startsWith('/api/') || request.path.startsWith('/health/')).map(request => request.path).sort()).toEqual(['/api/live/config', '/health/live']);

  await page.getByRole('button', { name: 'Load synthetic preview' }).click();
  await expect(page.getByTestId('preview-state')).toHaveText('Loaded · idle');
  await expect(page.getByTestId('flight-tick')).toHaveText('0');
  const initial = await page.getByTestId('flight-position').textContent();
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
  await page.waitForTimeout(250);
  await expect(page.getByTestId('flight-position')).toHaveText(stopped!);
  await expect(page.getByTestId('preview-state')).toHaveText('Stopped · frozen');
  await page.getByRole('button', { name: 'Reset preview' }).click();
  await expect(page.getByTestId('flight-tick')).toHaveText('0');
  await expect(page.getByTestId('flight-position')).toHaveText(initial!);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.reload();
  await expect(page.getByText('Idle · local service available')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Play synthetic preview' })).toBeDisabled();
  await expect(page.getByTestId('flight-canvas').locator('canvas')).toHaveCount(1);
  await expect(page.getByRole('alert')).toHaveCount(0);
  await expect(page.getByText('Explicit selection required')).toBeVisible();
  await expect(page.getByText('Off by default')).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  expect(requests.filter(request => request.path === '/api/live/flight-preview')).toHaveLength(1);
  expect(requests.every(request => request.method === 'GET')).toBe(true);
  expect(unexpectedOrigins).toEqual([]); expect(pageErrors).toEqual([]);
});

test('unavailable WebGL shows a usable honest fallback', async ({ page }) => {
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function(this: HTMLCanvasElement, kind: string, ...args: unknown[]) {
      if (kind.startsWith('webgl')) return null;
      return (original as any).apply(this, [kind, ...args]);
    } as typeof original;
  });
  await page.goto('/live');
  await expect(page.getByText(/3D view unavailable/)).toBeVisible();
  await page.getByRole('button', { name: 'Load synthetic preview' }).click();
  await expect(page.getByTestId('preview-state')).toHaveText('Loaded · idle');
  await expect(page.getByRole('button', { name: 'Play synthetic preview' })).toBeDisabled();
  await expect(page.getByTestId('flight-tick')).toHaveText('0');
});
