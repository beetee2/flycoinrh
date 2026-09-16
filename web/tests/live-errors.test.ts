import { describe, expect, it, vi } from 'vitest';
import { apiError, SessionClient } from '../src/live/session-client';
import examples from '../src/live/generated/examples.json';

const json = (body: unknown) => new Response(JSON.stringify(body), { status: 503, headers: { 'Content-Type': 'application/json' } });
const safeError = () => structuredClone(examples.find(item => item.contract === 'ApiError' && item.valid)!.value) as { message: string; code: string };

describe('bounded API error disclosure', () => {
  it('shows the strict server message and stable code', async () => {
    const body = safeError();
    expect((await apiError(json(body))).message).toBe(`${body.message} (${body.code})`);
  });
  it.each([
    { detail: '<script>private secret</script>' },
    { detail: 'Traceback /home/private/password' },
    { schema_version: 'obs-error-1', code: 'inference_unavailable', message: '/home/private token=secret' },
    { schema_version: 'obs-error-1', code: 'invented', message: 'secret' },
    { detail: 'x'.repeat(10000) },
  ])('rejects untrusted error detail %#', async body => {
    expect((await apiError(json(body))).message).toBe('Local request failed (HTTP 503). Check the launcher and source, then retry explicitly.');
  });
  it('ignores HTML and malformed JSON', async () => {
    for (const response of [new Response('<b>secret</b>', { status: 503 }), new Response('{', { status: 503, headers: { 'Content-Type': 'application/json' } })]) {
      expect((await apiError(response)).message).toContain('Check the launcher and source');
    }
  });
  it('cancels oversized streaming errors without consuming the rest', async () => {
    let cancelled = false;
    const response = new Response(new ReadableStream({ start(controller) { controller.enqueue(new Uint8Array(2049)); }, cancel() { cancelled = true; } }), { status: 503, headers: { 'Content-Type': 'application/json' } });
    expect((await apiError(response)).message).toContain('HTTP 503');
    expect(cancelled).toBe(true);
  });
  it('bounds a stalled error stream and cancels it', async () => {
    vi.useFakeTimers();
    let cancelled = false;
    try {
      const response = new Response(new ReadableStream({ cancel() { cancelled = true; } }), { status: 503, headers: { 'Content-Type': 'application/json' } });
      const pending = apiError(response);
      await vi.advanceTimersByTimeAsync(2000);
      expect((await pending).message).toContain('HTTP 503');
      expect(cancelled).toBe(true);
    } finally { vi.useRealTimers(); }
  });
  it('uses the safe error for session transport failures', async () => {
    const body = safeError();
    const client = new SessionClient({ fetch: async () => json(body), onSnapshot() {}, onNeutral() {} });
    try { await expect(client.sources()).rejects.toThrow(body.message); }
    finally { client.dispose(); }
  });
});
