import { test, expect } from '@playwright/test';

test('synthetic lab HTTP journey: exact keyboard edit, explicit submit, failure and reload', async ({ page }) => {
  const requests = async () => (await (await page.request.get('/fixture/requests')).json()).requests;
  const before = (await requests()).length;
  await page.goto('/lab');
  await expect(page.getByRole('status', { name: 'Local model status' })).toContainText('SYNTHETIC browser fixture');
  expect((await requests()).length).toBe(before);
  await page.getByRole('combobox', { name: 'Preset for A' }).selectOption('Black');
  await page.getByRole('combobox', { name: 'Preset for B' }).selectOption('White');
  await page.getByRole('slider', { name: 'Brush intensity for A' }).fill('73');
  await page.getByRole('button', { name: 'A pixel row 1 column 1: 0', exact: true }).focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('button', { name: 'A pixel row 1 column 1: 73', exact: true })).toBeVisible();
  const a = Array(256).fill(0); a[0] = 73;
  const response = page.waitForResponse(r => r.url().endsWith('/api/lab/compare'));
  await page.getByRole('button', { name: /Run comparison/ }).click();
  expect((await response).status()).toBe(503);
  await expect(page.getByRole('alert')).toContainText('SYNTHETIC browser fixture: no model calls or result');
  expect((await requests()).slice(before)).toEqual([
    { schema_version: 'flytrap-lab-request-1', a, b: Array(256).fill(255) },
  ]);
  await expect(page.getByRole('region', { name: 'Comparison result' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: /Run comparison/ })).toBeEnabled();
  expect((await page.request.get('/health/live')).status()).toBe(200);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.reload();
  await expect(page.getByRole('status', { name: 'Local model status' })).toContainText('SYNTHETIC browser fixture');
  expect((await requests()).length).toBe(before + 1);
  expect((await (await page.request.get('/fixture/requests')).json()).model_calls).toBe(0);
});
