import { expect, test } from '@playwright/test';

test('actual fixture API opens in the browser with honest capabilities', async ({ page, request }, testInfo) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => errors.push(error.message));
  const configResponse = page.waitForResponse((response) => response.url().endsWith('/api/config'));
  await page.goto('/');
  const response = await configResponse;
  expect(response.status()).toBe(200);
  expect(await response.json()).toMatchObject({ schema_version: '1', fixture: true, real_model_available: false, admission: 'closed', learning_claim_status: 'NOT_RUN' });
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('A small world.An inspectable experiment.');
  await expect(page.getByRole('note')).toHaveText('FIXTURE — NOT REAL MODEL');
  await expect(page.getByRole('status')).toHaveText('Real model unavailable');
  await expect(page.getByText('Closed', { exact: true })).toBeVisible();
  const health = await request.get('/health/live');
  expect(health.status()).toBe(200);
  expect(await health.json()).toEqual({ status: 'ok' });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', { name: 'FLYTRAP home' })).toBeFocused();
  expect(errors).toEqual([]);
  await page.screenshot({ path: testInfo.outputPath('foundation.png'), fullPage: true });
});
