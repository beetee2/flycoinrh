import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { SessionClient } from '../src/live/session-client';
import { parseLiveContract, type ApiSnapshot, type SessionConfig } from '../src/live/contracts';
import examples from '../src/live/generated/examples.json';
import recorded from './fixtures/recorded-flight.json';

function fixture(name: string) {
  return structuredClone(examples.find(example => example.contract === name && example.valid)!.value);
}
function snapshot(sequence = 1, overrides: Partial<ApiSnapshot> = {}): ApiSnapshot {
  const stream = parseLiveContract('StreamEnvelope', fixture('StreamEnvelope'));
  return parseLiveContract('ApiSnapshot', { ...stream, status: { ...stream.status, state: 'running' }, schema_version: 'obs-api-snapshot-1',
    event_sequence: sequence, kind: 'session', lease_remaining_ms: 3000,
    source_receipt_age_ms: null, response_age_ms: null, last_inferred: stream.neural_sample,
    capture_hz: 30, model_mode: 'fixture',
    completed_calls: 0, rejected_results: 0, model_hz: 0, last_step_wall_ms: null,
    recording_id: null, recording_state: 'off', ...overrides });
}
const config = () => fixture('SessionConfig') as SessionConfig;
const reply = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });
const bootstrap = {
  schema_version: 'obs-control-1', csrf_token: `${'a'.repeat(32)}.${'b'.repeat(64)}`,
  recording_notice: 'Recording is optional and off by default. Consent saves private processed 16x16 inputs, raw neural responses and flight replay locally. These inputs can contain sensitive content. Full-resolution source video is never saved.',
};
class TestStream extends EventTarget {
  closed = false;
  close() { this.closed = true; }
  send(value: unknown) { this.dispatchEvent(new MessageEvent('snapshot', { data: JSON.stringify(value) })); }
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>(done => { resolve = done; });
  return { promise, resolve };
}

describe('OBS04 browser transport and owner lease, synthetic responses only', () => {
  const clients: SessionClient[] = [];
  beforeEach(() => { vi.useFakeTimers(); });
  afterEach(() => { clients.forEach(client => client.dispose()); clients.length = 0; vi.useRealTimers(); });

  function setup(handler?: (url: string, init?: RequestInit) => Promise<Response>) {
    const doc = Object.assign(new EventTarget(), { hidden: false });
    const win = new EventTarget();
    const streams: TestStream[] = [];
    const onSnapshot = vi.fn();
    const onNeutral = vi.fn();
    let sequence = 0;
    const transport = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (handler) return handler(url, init);
      const result = snapshot(++sequence);
      return reply(url.endsWith('/control') ? bootstrap : url.endsWith('/preview') ? {
        ...result, kind: 'preview', model_mode: 'none', flight: null, neural_sample: null, last_inferred: null,
      } : result);
    });
    const client = new SessionClient({ fetch: transport as typeof fetch, document: doc, window: win,
      eventSource: () => { const stream = new TestStream(); streams.push(stream); return stream; },
      now: () => Date.now() + 8_000_000, onSnapshot, onNeutral });
    clients.push(client);
    return { client, transport, doc, win, streams, onSnapshot, onNeutral };
  }
  const writes = (transport: ReturnType<typeof setup>['transport']) => transport.mock.calls.filter(([, init]) => init?.method === 'POST');

  it('starts only explicitly, bootstraps CSRF, and generates unique tab owners and request IDs', async () => {
    const first = setup(), second = setup();
    expect(first.transport).not.toHaveBeenCalled();
    await first.client.start(config());
    await second.client.preview(config().source_id);
    const [url, init] = writes(first.transport)[0];
    expect(url).toBe('/api/live/sessions');
    expect(init?.credentials).toBe('same-origin');
    expect(init?.headers).toEqual({ 'Content-Type': 'application/json', 'X-Live-CSRF': bootstrap.csrf_token });
    const request = JSON.parse(init!.body as string);
    const other = JSON.parse(writes(second.transport)[0][1]!.body as string);
    expect(request.owner_token).toMatch(/^[0-9a-f]{32}$/);
    expect(request.request_id).toMatch(/^[0-9a-f]{32}$/);
    expect(request.owner_token).not.toBe(other.owner_token);
    expect(request.request_id).not.toBe(other.request_id);
    expect(request.recording_consent).toBe(false);
    expect(request.config.recording).toBe(false);
    await expect(first.client.start(config())).rejects.toThrow(/another session/);
    expect(writes(first.transport)).toHaveLength(1);
  });

  it('requires recording consent on every explicit Start and validates requests before fetch', async () => {
    const { client, transport } = setup();
    expect(() => client.start({ ...config(), recording: true })).toThrow();
    expect(() => client.preview('../desktop')).toThrow();
    expect(transport).not.toHaveBeenCalled();
    await client.start({ ...config(), recording: true }, true);
    expect(JSON.parse(writes(transport)[0][1]!.body as string).recording_consent).toBe(true);
  });

  it('renews within one second using a local duration despite unrelated server clock origin', async () => {
    const { client, transport, onNeutral } = setup();
    await client.start(config());
    await vi.advanceTimersByTimeAsync(1000);
    expect(writes(transport).map(([url]) => url)).toEqual(['/api/live/sessions', `/api/live/sessions/${snapshot().status.session_id}/renew`]);
    await vi.advanceTimersByTimeAsync(1000);
    expect(writes(transport).filter(([url]) => String(url).endsWith('/renew'))).toHaveLength(2);
    expect(onNeutral).not.toHaveBeenCalled();
  });

  it.each(['visibilitychange', 'pagehide'])('releases on %s with protected keepalive Stop and no future renewal', async event => {
    const { client, transport, doc, win, onNeutral } = setup();
    await client.start(config());
    if (event === 'visibilitychange') doc.hidden = true;
    (event === 'pagehide' ? win : doc).dispatchEvent(new Event(event));
    const stop = writes(transport).at(-1)!;
    expect(stop[0]).toMatch(/\/stop$/);
    expect(stop[1]?.keepalive).toBe(true);
    expect(stop[1]?.headers).toHaveProperty('X-Live-CSRF', bootstrap.csrf_token);
    expect(onNeutral).toHaveBeenCalledOnce();
    await vi.advanceTimersByTimeAsync(10_000);
    expect(writes(transport)).toHaveLength(2);
    client.dispose(); client.dispose();
    win.dispatchEvent(new Event('pagehide'));
    expect(writes(transport)).toHaveLength(2);
  });

  it('freezes immediately after a failed renewal and sends Stop without retrying ownership', async () => {
    const { client, transport, onNeutral } = setup(async url =>
      reply(url.endsWith('/control') ? bootstrap : snapshot(), url.endsWith('/renew') ? 409 : 200));
    await client.start(config());
    await vi.advanceTimersByTimeAsync(1000);
    expect(onNeutral).toHaveBeenCalledWith('Control renewal failed.');
    expect(writes(transport).map(([url]) => String(url).split('/').at(-1))).toEqual(['sessions', 'renew', 'stop']);
    await vi.advanceTimersByTimeAsync(10_000);
    expect(writes(transport)).toHaveLength(3);
  });

  it('expires while renewal is hung; late renewal cannot restart timers or restore motion', async () => {
    const late = deferred<Response>();
    const { client, transport, onNeutral, onSnapshot } = setup(async url =>
      url.endsWith('/renew') ? late.promise : reply(url.endsWith('/control') ? bootstrap : snapshot()));
    await client.start(config());
    await vi.advanceTimersByTimeAsync(3000);
    expect(onNeutral).toHaveBeenCalledWith('Control lease expired.');
    late.resolve(reply(snapshot(20)));
    await vi.advanceTimersByTimeAsync(10_000);
    expect(onSnapshot).toHaveBeenCalledTimes(1);
    expect(writes(transport)).toHaveLength(3);
  });

  it('subtracts response travel time from the server lease duration', async () => {
    const pending = deferred<Response>();
    const { client, onNeutral } = setup(async url => url.endsWith('/control') ? reply(bootstrap) : pending.promise);
    const started = client.start(config());
    await vi.advanceTimersByTimeAsync(0);
    await vi.advanceTimersByTimeAsync(3100);
    pending.resolve(reply(snapshot()));
    await started;
    expect(onNeutral).toHaveBeenCalledWith('Control lease expired.');
  });

  it('hiding during an in-flight Start releases the returned owner without accepting its state', async () => {
    const pending = deferred<Response>();
    const { client, doc, transport, onSnapshot } = setup(async url =>
      url.endsWith('/sessions') ? pending.promise : reply(url.endsWith('/control') ? bootstrap : snapshot()));
    const started = client.start(config());
    const rejection = expect(started).rejects.toThrow(/released/);
    await vi.advanceTimersByTimeAsync(0);
    doc.hidden = true; doc.dispatchEvent(new Event('visibilitychange'));
    pending.resolve(reply(snapshot()));
    await rejection;
    expect(onSnapshot).not.toHaveBeenCalled();
    expect(writes(transport).at(-1)![0]).toMatch(/\/stop$/);
  });

  it('hiding during bootstrap cancels before Start and opens no source', async () => {
    const pending = deferred<Response>();
    const { client, doc, transport } = setup(async () => pending.promise);
    const started = client.start(config());
    const rejection = expect(started).rejects.toThrow(/before capture/);
    doc.hidden = true; doc.dispatchEvent(new Event('visibilitychange'));
    pending.resolve(reply(bootstrap));
    await rejection;
    expect(writes(transport)).toHaveLength(0);
  });

  it('spectators reconnect passively, deduplicate snapshots, and reject older HTTP after newer SSE', async () => {
    const pending = deferred<Response>();
    const { client, streams, transport, onSnapshot } = setup(async () => (await pending.promise).clone());
    const first = snapshot();
    const connection = client.connect(first.status.session_id, first.status.generation);
    streams[0].send(snapshot(10));
    streams[0].send(snapshot(10));
    streams[0].send(snapshot(9));
    pending.resolve(reply(snapshot(1)));
    await connection;
    expect(onSnapshot.mock.calls.map(([s]) => s.event_sequence)).toEqual([10]);
    await vi.advanceTimersByTimeAsync(10_000);
    expect(writes(transport)).toHaveLength(0);
    const next = client.connect(first.status.session_id, first.status.generation);
    expect(streams[0].closed).toBe(true);
    streams[0].send(snapshot(50));
    streams[1].send(snapshot(11));
    await next;
    expect(onSnapshot.mock.calls.map(([s]) => s.event_sequence)).toEqual([10, 11]);
  });

  it('ignores foreign session/generation events and neutralizes corrupted stream data', async () => {
    const { client, streams, transport, onSnapshot, onNeutral } = setup();
    const first = snapshot();
    await client.connect(first.status.session_id, first.status.generation);
    const foreign = snapshot(2, { latest_source_frame: null, neural_sample: null, flight: null });
    foreign.status = { ...foreign.status, session_id: 'foreign', generation: 3 };
    streams[0].send(foreign);
    expect(onSnapshot).toHaveBeenCalledTimes(1);
    streams[0].send({ ...first, untrusted_field: true });
    expect(onNeutral).toHaveBeenCalledWith('Invalid session stream.');
    expect(streams[0].closed).toBe(true);
    expect(writes(transport)).toHaveLength(0);
  });

  it('disconnect neutralizes an owner and closes the stream; spectators never send Stop', async () => {
    const owner = setup(), spectator = setup();
    const first = await owner.client.start(config());
    await owner.client.connect(first.status.session_id, first.status.generation);
    await spectator.client.connect(first.status.session_id, first.status.generation);
    owner.streams[0].dispatchEvent(new Event('error'));
    spectator.streams[0].dispatchEvent(new Event('error'));
    expect(owner.onNeutral).toHaveBeenCalledWith('Session connection lost.');
    expect(writes(owner.transport).at(-1)![0]).toMatch(/\/stop$/);
    expect(writes(spectator.transport)).toHaveLength(0);
    await vi.advanceTimersByTimeAsync(10_000);
    expect(writes(owner.transport)).toHaveLength(2);
  });

  it('terminal snapshots end timers and older live responses cannot revive the owner', async () => {
    const { client, streams, transport, onSnapshot, onNeutral } = setup();
    const first = await client.start(config());
    await client.connect(first.status.session_id, first.status.generation);
    const ended = snapshot(10);
    ended.status.state = 'stopped';
    streams[0].send(ended);
    streams[0].send(snapshot(11));
    await vi.advanceTimersByTimeAsync(10_000);
    expect(onNeutral).toHaveBeenCalledWith('Session is terminal.');
    expect(onSnapshot.mock.calls.at(-1)![0].status.state).toBe('stopped');
    expect(writes(transport)).toHaveLength(1);
  });

  it('rejects invalid HTTP snapshots, unsafe session paths, and oversized stream messages', async () => {
    const { client, streams, transport, onNeutral } = setup(async () => reply({ invalid: true }));
    await expect(client.connect('../outside', 1)).rejects.toThrow(/identity/);
    expect(transport).not.toHaveBeenCalled();
    await expect(client.connect('safe', 1)).rejects.toThrow(/schema/);
    expect(onNeutral).toHaveBeenCalledWith('Session snapshot unavailable.');
    const clean = setup();
    const first = snapshot();
    await clean.client.connect(first.status.session_id, first.status.generation);
    clean.streams[0].dispatchEvent(new MessageEvent('snapshot', { data: ' '.repeat(262145) }));
    expect(clean.onNeutral).toHaveBeenCalledWith('Invalid session stream.');
    expect(streams[0].closed).toBe(true);
  });

  it('binds replay load and seek to the listed session without capture or control requests', async () => {
    const id = 'f'.repeat(32);
    let foreign = false;
    const { client, transport } = setup(async url => {
      if (url.endsWith('/replays')) return reply({ schema_version: 'obs-replay-list-1', recordings: [
        { recording_id: id, manifest: recorded.manifest, state: null, error: null },
      ] });
      if (url.includes('/seek')) return reply({ ...recorded.final, snapshot: { ...recorded.final.snapshot,
        session_id: foreign ? 'foreign' : recorded.manifest.session_id } });
      return reply(recorded);
    });
    await expect(client.replay(id)).rejects.toThrow(/Refresh recordings/);
    await client.replays();
    const payload = await client.replay(id);
    expect(payload.samples[0].observation_u8).toEqual(recorded.inputs[0].observation_u8);
    expect((await client.seek(id, recorded.final.snapshot.tick)).snapshot).toEqual(recorded.final.snapshot);
    foreign = true;
    await expect(client.seek(id, recorded.final.snapshot.tick)).rejects.toThrow(/Foreign replay/);
    await expect(client.seek(id, -1)).rejects.toThrow(/tick/);
    expect(writes(transport)).toHaveLength(0);
  });

  it('rejects valid-schema recording data with foreign inputs or altered raw neural values', () => {
    const foreign = structuredClone(recorded);
    foreign.inputs[0].frame.session_id = 'foreign';
    expect(() => parseLiveContract('ReplayPayload', foreign)).toThrow(/identity/);
    const altered = structuredClone(recorded);
    altered.results[0].motor_rates_hz.fwd_L += 1;
    expect(() => parseLiveContract('ReplayPayload', altered)).toThrow(/neural values/);
    const controls = structuredClone(recorded);
    controls.trace.events.find(event => event.controls)!.controls!.response_id = 'foreign';
    expect(() => parseLiveContract('ReplayPayload', controls)).toThrow(/foreign replay controls/);
  });

  it('does not accept a late passive response after Stop', async () => {
    const pending = deferred<Response>();
    const { client, onSnapshot } = setup(async () => pending.promise);
    const first = snapshot();
    const connection = client.connect(first.status.session_id, first.status.generation);
    client.stop();
    pending.resolve(reply(first));
    await connection;
    expect(onSnapshot).not.toHaveBeenCalled();
  });

  it('rejects source switching and regressing flight ticks even inside newer valid envelopes', async () => {
    const { client, streams, onSnapshot, onNeutral } = setup();
    const first = await client.start(config());
    await client.connect(first.status.session_id, first.status.generation);
    const progressed = snapshot(10);
    progressed.flight!.tick = 10;
    streams[0].send(progressed);
    streams[0].send(snapshot(11));
    expect(onSnapshot.mock.calls.at(-1)![0].flight.tick).toBe(10);
    const switched = snapshot(12);
    switched.latest_source_frame!.source_id = 'another-source';
    switched.neural_sample!.frame.source_id = 'another-source';
    switched.last_inferred!.frame.source_id = 'another-source';
    streams[0].send(switched);
    expect(onNeutral).toHaveBeenCalledWith('Session source identity changed.');
    expect(streams[0].closed).toBe(true);
  });

  it('rejects a wrong-source Start acknowledgement and sends protected Stop', async () => {
    const { client, transport } = setup();
    await expect(client.start({ ...config(), source_id: 'another-source' })).rejects.toThrow(/rejected/);
    expect(writes(transport).at(-1)![0]).toMatch(/\/stop$/);
  });

  it('downloads validated original recording JSON without rewriting negative zero', async () => {
    vi.useRealTimers();
    const id = 'e'.repeat(32);
    const data = structuredClone(recorded);
    data.samples[0].raw_action.dy = data.results[0].raw_action.dy = data.results[0].output.dy = 0;
    const original = JSON.stringify(data).replaceAll('"dy":0', '"dy":-0.0');
    const { client, transport } = setup(async url => url.endsWith('/replays') ? reply({
      schema_version: 'obs-replay-list-1', recordings: [{ recording_id: id, manifest: recorded.manifest }],
    }) : new Response(original));
    await client.replays();
    const blob = await client.download(id);
    const text = await new Promise<string>(resolve => {
      const reader = new FileReader(); reader.onload = () => resolve(reader.result as string); reader.readAsText(blob);
    });
    expect(text).toBe(original);
    expect(text).toContain('"dy":-0.0');
    expect(writes(transport)).toHaveLength(0);
  });
});
