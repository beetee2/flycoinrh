import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import axe from 'axe-core';
import { assertDisplayedSnapshot, current, ledgers, replayRecorded, selectLive, startBounded, terminal } from './journeyHelpers';
import { attachErrors, collectErrors, recordGraphics } from './graphicsDiagnostics';

const root = path.resolve('..');
const fixtureRoot = () => readFileSync(path.join(root, 'artifacts/live/browser-fixture/fixture-root.txt'), 'utf8');

test('actual fixture API: keyboard preview, exact neural input and pose, private opt-in replay', async ({ page, browser }, info) => {
  const errors = collectErrors(page);
  try {
    const graphics = await recordGraphics(page, browser, info);
    expect(graphics.flightAttributes.available).toBe(true);
    const initialLedgers = ledgers(root);
    await selectLive(page);
    await expect(page.getByLabel('Record this session locally', { exact: true })).not.toBeChecked();
    const preview = page.getByRole('button', { name: 'Preview source', exact: true });
    await preview.focus();
    await expect(preview).toBeFocused();
    await preview.press('Enter');
    await expect.poll(async () => (await current(page))?.status.state).toBe('previewing');
    await expect(page.getByTestId('source-preview-id')).toContainText('fixture-pattern');
    await expect.poll(async () => JSON.parse((await page.getByTestId('source-preview-bytes').textContent())!).length).toBe(256);
    expect((await current(page))?.status.attempted_calls).toBe(0);
    expect(ledgers(root)).toEqual(initialLedgers);
    await page.getByRole('button', { name: 'Stop session', exact: true }).click();
    expect((await terminal(page)).status.state).toBe('stopped');
    await startBounded(page, 8, true);
    const final = await terminal(page);
    expect(final.status.state, final.status.reason ?? '').toBe('limit_reached');
    expect(final.status.attempted_calls).toBe(8);
    expect(final.completed_calls).toBe(8);
    expect(final.model_mode).toBe('fixture');
    await assertDisplayedSnapshot(page, final);
    const screenshot = info.outputPath(`fixture-flight-${info.project.name}.png`);
    await page.screenshot({ path: screenshot, fullPage: true });
    await info.attach('safe fixture flight', { path: screenshot, contentType: 'image/png' });
    await page.evaluate(axe.source);
    const accessibility = await page.evaluate(async () => (window as unknown as { axe: typeof axe }).axe.run(document, {
      runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa'] },
    }));
    await info.attach('accessibility', { body: JSON.stringify(accessibility.violations, null, 2), contentType: 'application/json' });
    expect(accessibility.violations).toEqual([]);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await replayRecorded(page, final, fixtureRoot(), info);
    expect(ledgers(root), 'synthetic graph cannot consume the real ledgers').toEqual(initialLedgers);
    expect(errors.pageErrors).toEqual([]);
    expect(errors.consoleErrors).toEqual([]);
  } finally { await attachErrors(info, errors); }
});

for (const fault of ['hidden', 'transport', 'graphics', 'reload'] as const) {
  test(`active fixture ${fault} releases capture and inference; recovery remains explicit`, async ({ page }) => {
    await selectLive(page);
    await startBounded(page, 512);
    await expect.poll(async () => (await current(page))?.completed_calls).toBeGreaterThan(0);
    const active = await current(page);
    if (fault === 'hidden') {
      await page.evaluate(() => {
        Object.defineProperty(document, 'hidden', { configurable: true, get: () => true });
        document.dispatchEvent(new Event('visibilitychange'));
      });
    } else if (fault === 'transport') {
      await page.context().setOffline(true);
      await page.waitForTimeout(3500);
      await page.context().setOffline(false);
    } else if (fault === 'graphics') {
      const lost = await page.getByTestId('flight-canvas').locator('canvas').evaluate(canvas => {
        const extension = (canvas as HTMLCanvasElement).getContext('webgl2')?.getExtension('WEBGL_lose_context');
        extension?.loseContext(); return Boolean(extension);
      });
      expect(lost).toBe(true);
      await expect(page.getByTestId('graphics-state')).toHaveText('Context lost');
    } else { await page.reload(); }
    const stopped = await terminal(page, 7000);
    expect(stopped.status.session_id).toBe(active!.status.session_id);
    expect(stopped.status.state).toBe('stopped');
    expect(stopped.flight?.neutral).toBe(true);
    const calls = stopped.status.attempted_calls;
    if (fault === 'hidden') {
      await page.evaluate(() => {
        Object.defineProperty(document, 'hidden', { configurable: true, get: () => false });
        document.dispatchEvent(new Event('visibilitychange'));
      });
    } else if (fault === 'graphics') {
      await page.getByRole('button', { name: 'Retry graphics', exact: true }).click();
      await expect(page.getByTestId('graphics-state')).toHaveText('Ready');
    }
    await page.waitForTimeout(250);
    expect((await current(page))?.status.attempted_calls).toBe(calls);
    expect((await current(page))?.flight).toEqual(stopped.flight);
    await expect(page.getByTestId('flight-canvas').locator('canvas')).toHaveCount(1);
  });
}
