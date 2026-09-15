import { test, expect } from '@playwright/test';

// Actual HTTP and built UI, idle service only. No capture or model source.
test('idle page mounts and reloads without capture, inference, or browser errors', async ({ page }) => {
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
  await expect(page.getByRole('status')).toHaveText('Idle · foundation service available');
  await expect(page.getByText(/Capture and inference are unavailable in OBS00/)).toBeVisible();
  await expect(page.getByText('Explicit selection required')).toBeVisible();
  await expect(page.getByText('Off by default')).toBeVisible();
  await expect(page.getByRole('button')).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);

  await page.reload();
  await expect(page.getByRole('status')).toHaveText('Idle · foundation service available');
  await expect(page.getByRole('alert')).toHaveCount(0);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);

  const serviceReads = requests.filter(request => request.path.startsWith('/api/') || request.path.startsWith('/health/'));
  expect(serviceReads).toHaveLength(4);
  expect(serviceReads.filter(request => request.path === '/health/live')).toHaveLength(2);
  expect(serviceReads.filter(request => request.path === '/api/live/config')).toHaveLength(2);
  expect(requests.every(request => request.method === 'GET')).toBe(true);
  expect(unexpectedOrigins).toEqual([]);
  expect(pageErrors).toEqual([]);
});
