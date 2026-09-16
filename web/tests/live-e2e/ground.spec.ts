import { test, expect } from '@playwright/test';
import { attachErrors, collectErrors } from './graphicsDiagnostics';

// Actual HTTP synthetic preview, with no source selection or inference request.
test('ground descent, contact, departure and Stop render faithfully', async ({ page }, info) => {
  test.setTimeout(40_000);
  const errors = collectErrors(page), mutations: string[] = [];
  page.on('request', request => { if (request.method() !== 'GET') mutations.push(request.url()); });
  try {
    const response = await page.request.get('/api/live/flight-preview');
    expect(response.ok()).toBe(true);
    const preview = await response.json();
    const snapshots = preview.snapshots;
    expect(snapshots.every((pose: any) => pose.schema_version === 'obs-flight-2' && pose.physics_id === 'flight-fixed20-ground-v2')).toBe(true);
    const environment = snapshots[0].environment;
    const minimum = environment.ground_z + environment.clearance;
    expect(snapshots.every((pose: any) => pose.position[2] >= minimum)).toBe(true);
    await page.goto('/live');
    await expect(page.getByTestId('graphics-state')).toHaveText('Ready');
    await page.getByRole('button', { name: 'Load synthetic preview' }).click();
    await expect(page.getByTestId('preview-state')).toHaveText('Loaded · idle');
    await page.evaluate(() => {
      const root = document.querySelector('[data-testid="rendered-pose"]')!;
      const collected: unknown[] = [];
      (window as any).groundFrames = collected;
      new MutationObserver(() => { if (root.textContent) collected.push(JSON.parse(root.textContent)); }).observe(root, { childList: true, characterData: true, subtree: true });
    });
    const canvas = page.getByTestId('flight-canvas');
    async function screenshot(name: string) {
      await canvas.scrollIntoViewIfNeeded();
      const filename = info.outputPath(`${name}-${info.project.name}.png`);
      await canvas.screenshot({ path: filename });
      await info.attach(name, { path: filename, contentType: 'image/png' });
    }
    await page.getByRole('button', { name: 'Play synthetic preview' }).click();
    await expect.poll(async () => Number(await page.getByTestId('flight-tick').textContent())).toBeGreaterThan(65);
    await screenshot('descent');
    await expect(page.getByTestId('ground-contact')).toHaveText('Contact · downward motion constrained', { timeout: 8000 });
    await screenshot('contact');
    const contact = JSON.parse((await page.getByTestId('rendered-pose').textContent())!);
    expect(contact.position[2]).toBe(minimum);
    await page.getByRole('button', { name: 'Pause', exact: true }).click();
    const frozen = await page.getByTestId('rendered-pose').textContent();
    await page.waitForTimeout(150);
    await expect(page.getByTestId('rendered-pose')).toHaveText(frozen!);
    await page.getByRole('button', { name: 'Play synthetic preview' }).click();
    await expect.poll(async () => Number(await page.getByTestId('flight-tick').textContent()), { timeout: 10000 }).toBeGreaterThan(500);
    await expect(page.getByTestId('ground-contact')).toHaveText('Clear');
    await screenshot('departure');
    const departure = JSON.parse((await page.getByTestId('rendered-pose').textContent())!);
    expect(departure.position[2]).toBeGreaterThan(minimum + .1);
    await page.getByRole('button', { name: 'Stop', exact: true }).click();
    const stopped = await page.getByTestId('rendered-pose').textContent();
    await page.waitForTimeout(150);
    await expect(page.getByTestId('rendered-pose')).toHaveText(stopped!);
    const frames = await page.evaluate(() => (window as any).groundFrames);
    expect(frames.length).toBeGreaterThan(50);
    expect(frames.every((pose: any) => pose.position[2] >= minimum)).toBe(true);
    expect(frames.some((pose: any) => pose.ground_contact)).toBe(true);
    // Linear center interpolation stays in a convex half-space. The tested
    // constant geometry envelope also covers every interpolated orientation.
    await info.attach('rendered-ground-frames', { body: JSON.stringify({ environment, frames }), contentType: 'application/json' });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    expect(mutations).toEqual([]);
    expect(errors.pageErrors).toEqual([]); expect(errors.consoleErrors).toEqual([]);
  } finally { await attachErrors(info, errors); }
});
