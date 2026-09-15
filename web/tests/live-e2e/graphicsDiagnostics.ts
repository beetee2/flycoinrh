import type { Browser, Page, TestInfo } from '@playwright/test';
import { FLIGHT_CONTEXT_ATTRIBUTES } from '../../src/live/flightRenderer';

/** Standalone canvases are probed before Flyjam loads, then explicitly released. */
export async function recordGraphics(page: Page, browser: Browser, info: TestInfo) {
  let processGraphics: unknown;
  try {
    const session = await browser.newBrowserCDPSession();
    try {
      const system = await session.send('SystemInfo.getInfo');
      processGraphics = { commandLine: system.commandLine, gpu: system.gpu };
    } finally { await session.detach(); }
  } catch (error) { processGraphics = { unavailable: String(error) }; }
  const contexts = await page.evaluate(attributes => {
    const probe = (requested?: WebGLContextAttributes) => {
      const canvas = document.createElement('canvas');
      const creationErrors: string[] = [];
      canvas.addEventListener('webglcontextcreationerror', event => creationErrors.push((event as WebGLContextEvent).statusMessage));
      let gl: WebGL2RenderingContext | null = null;
      try {
        gl = canvas.getContext('webgl2', requested);
        if (!gl) return { available: false, requested: requested ?? 'browser defaults', creationErrors };
        const debug = gl.getExtension('WEBGL_debug_renderer_info');
        return {
          available: true, requested: requested ?? 'browser defaults', actual: gl.getContextAttributes(), creationErrors,
          vendor: gl.getParameter(gl.VENDOR), renderer: gl.getParameter(gl.RENDERER), version: gl.getParameter(gl.VERSION),
          unmaskedVendor: debug ? gl.getParameter(debug.UNMASKED_VENDOR_WEBGL) : null,
          unmaskedRenderer: debug ? gl.getParameter(debug.UNMASKED_RENDERER_WEBGL) : null,
          unavailableFields: debug ? [] : ['WEBGL_debug_renderer_info (extension unavailable)'],
        };
      } catch (error) {
        return { available: false, requested: requested ?? 'browser defaults', creationErrors, exception: String(error) };
      } finally {
        gl?.getExtension('WEBGL_lose_context')?.loseContext(); canvas.remove();
      }
    };
    return { userAgent: navigator.userAgent, minimal: probe(), flightAttributes: probe(attributes) };
  }, FLIGHT_CONTEXT_ATTRIBUTES);
  const diagnostics = {
    project: info.project.name, browserVersion: browser.version(),
    executable: info.project.use.launchOptions?.executablePath ?? null,
    executableNote: info.project.use.launchOptions?.executablePath ? 'Exact configured binary; disposable Playwright profile.' : 'Playwright bundled browser selected by its launcher; see environment evidence for exact executable.',
    headless: info.project.use.headless, launchOptions: info.project.use.launchOptions ?? {},
    processGraphics,
    display: process.env.DISPLAY ?? null, waylandDisplay: process.env.WAYLAND_DISPLAY ?? null,
    contexts,
    limitation: 'Independent disposable browser session. This does not reproduce or certify the operator’s personal browser/profile.',
  };
  await info.attach('graphics-environment', { body: JSON.stringify(diagnostics, null, 2), contentType: 'application/json' });
  return contexts;
}

export function collectErrors(page: Page) {
  const consoleErrors: string[] = [], pageErrors: string[] = [];
  const consoleLocations: { text: string; url: string; lineNumber: number; columnNumber: number }[] = [];
  page.on('console', message => { if (message.type() === 'error') {
    consoleErrors.push(message.text()); consoleLocations.push({ text: message.text(), ...message.location() });
  } });
  page.on('pageerror', error => pageErrors.push(error.message));
  return { consoleErrors, consoleLocations, pageErrors };
}

export async function attachErrors(info: TestInfo, errors: ReturnType<typeof collectErrors>, forced = false) {
  await info.attach(forced ? 'forced-failure-errors' : 'normal-playback-errors', {
    body: JSON.stringify(errors, null, 2), contentType: 'application/json',
  });
}
