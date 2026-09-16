import { createElement } from 'react';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { DisplayBackpressureError, SessionClient } from '../src/live/session-client';
import { parseLiveContract, type ContractName, type LiveContracts } from '../src/live/contracts';
import { Live } from '../src/live/Live';
import examples from '../src/live/generated/examples.json';

// The UI retry test uses a labeled DOM stage: no WebGL, model or capture devices.
vi.mock('../src/live/FlightStage', async () => {
  const React = await import('react');
  return { FlightStage: (props: { onGraphicsReady?: () => void; backdropUrl?: string | null }) => {
    React.useEffect(() => { props.onGraphicsReady?.(); }, [props.onGraphicsReady]);
    return React.createElement('div', { 'data-testid': 'safe-fixture-stage', 'data-backdrop': props.backdropUrl ?? '' });
  } };
});

function fixture<K extends ContractName>(name: K): LiveContracts[K] {
  return parseLiveContract(name, structuredClone(examples.find(item => item.contract === name && item.valid)!.value));
}
const response = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });
const activeSnapshot = () => {
  const value = fixture('ApiSnapshot');
  value.status.state = 'running';
  value.lease_remaining_ms = 3000;
  return value;
};
const activeDisplay = () => {
  const value = fixture('DisplayReply');
  value.status.state = 'running';
  return value;
};
class FixtureStream extends EventTarget { close = vi.fn(); }
const clients: SessionClient[] = [];

afterEach(() => {
  cleanup();
  clients.splice(0).forEach(client => client.dispose());
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function setup(display: () => Promise<Response> = async () => response(activeDisplay())) {
  const clock = { now: 1000 };
  const onNeutral = vi.fn();
  const onSnapshot = vi.fn();
  const transport = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit) => {
    const path = String(input);
    if (path.endsWith('/control')) return response(fixture('ControlBootstrap'));
    if (path.endsWith('/display')) return display();
    return response(activeSnapshot());
  });
  const client = new SessionClient({ fetch: transport as typeof fetch,
    now: () => clock.now, onNeutral, onSnapshot, eventSource: () => new FixtureStream(),
    document: Object.assign(new EventTarget(), { hidden: false }), window: new EventTarget() });
  clients.push(client);
  return { client, transport, onNeutral, onSnapshot, clock };
}
const identity = fixture('ApiSnapshot').status;
const displayPath = `/api/live/sessions/${identity.session_id}/display`;

describe('SG01 presentation transport with original safe fixture JPEGs', () => {
  it('does not request pixels or acquire control without ownership, including passive reconnect', async () => {
    const { client, transport } = setup();
    await expect(client.displayFrame(identity.session_id, identity.generation)).rejects.toThrow(/ownership/);
    expect(transport).not.toHaveBeenCalled();
    await client.connect(identity.session_id, identity.generation);
    const before = transport.mock.calls.length;
    await expect(client.displayFrame(identity.session_id, identity.generation)).rejects.toThrow(/ownership/);
    expect(transport).toHaveBeenCalledTimes(before);
    expect(transport.mock.calls.every(([, init]) => !init?.method)).toBe(true);
  });

  it('sends selected owner, CSRF and generation with no-store, and preserves frame identity', async () => {
    const { client, transport, onSnapshot } = setup();
    await client.start(fixture('SessionConfig'));
    const abort = new AbortController();
    const result = await client.displayFrame(identity.session_id, identity.generation, abort.signal);
    expect(result).toEqual(activeDisplay());
    const [path, init] = transport.mock.calls.at(-1)!;
    expect(path).toBe(displayPath);
    expect(init).toMatchObject({ method: 'POST', credentials: 'same-origin', cache: 'no-store', signal: abort.signal,
      headers: { 'Content-Type': 'application/json', 'X-Live-CSRF': fixture('ControlBootstrap').csrf_token } });
    const start = JSON.parse(transport.mock.calls.find(([url]) => url === '/api/live/sessions')![1]!.body as string);
    expect(JSON.parse(init!.body as string)).toEqual({ generation: identity.generation, owner_token: start.owner_token });
    expect(onSnapshot).toHaveBeenCalledOnce(); // A display reply is not a neural/flight snapshot.
  });

  it.each([['foreign-session', 1], [identity.session_id, 2]] as const)(
    'rejects a requested foreign identity %s/%s before fetch', async (sessionId, generation) => {
      const { client, transport } = setup();
      await client.start(fixture('SessionConfig'));
      const before = transport.mock.calls.length;
      await expect(client.displayFrame(sessionId, generation)).rejects.toThrow(/ownership/);
      expect(transport).toHaveBeenCalledTimes(before);
    });

  it.each([1999, 2000, 2400])('accounts for receipt age plus full local round-trip at %s ms', async total => {
    const packet = activeDisplay();
    packet.latest!.receipt_age_ms = 1750;
    const context = setup(async () => {
      context.clock.now += total - 1750;
      return response(packet);
    });
    await context.client.start(fixture('SessionConfig'));
    const result = await context.client.displayFrame(identity.session_id, identity.generation);
    expect(result.latest).toEqual(total < 2000 ? packet.latest : null);
    expect(context.onNeutral).not.toHaveBeenCalled();
  });

  it.each(['unknown-version', 'unknown-field', 'oversized-envelope', 'invalid-jpeg'])(
    'rejects %s before presentation receives an image', async kind => {
      const packet = activeDisplay();
      const body: unknown = kind === 'unknown-version' ? { ...packet, schema_version: 'future-99' }
        : kind === 'unknown-field' ? { ...packet, caption: 'not an allowed transport setting' }
          : kind === 'invalid-jpeg' ? { ...packet, latest: { ...packet.latest, jpeg_base64: 'AAAA' } } : packet;
      const { client } = setup(async () => kind === 'oversized-envelope'
        ? new Response(' '.repeat(360449)) : response(body));
      await client.start(fixture('SessionConfig'));
      await expect(client.displayFrame(identity.session_id, identity.generation)).rejects.toThrow();
    });

  it.each(['source', 'session', 'generation'])('rejects a valid-schema foreign %s response', async kind => {
    const packet = activeDisplay();
    if (kind === 'source') packet.latest!.frame.source_id = 'foreign-source';
    if (kind === 'session') packet.status.session_id = packet.latest!.frame.session_id = 'foreign-session';
    if (kind === 'generation') packet.status.generation = packet.latest!.frame.generation = 2;
    const { client } = setup(async () => response(packet));
    await client.start(fixture('SessionConfig'));
    await expect(client.displayFrame(identity.session_id, identity.generation)).rejects.toThrow(/Foreign or expired/);
  });

  it('rejects an in-flight image after Stop and cannot reacquire from that response', async () => {
    let resolve!: (value: Response) => void;
    const pending = new Promise<Response>(done => { resolve = done; });
    const { client, transport, onSnapshot } = setup(() => pending);
    await client.start(fixture('SessionConfig'));
    const request = client.displayFrame(identity.session_id, identity.generation);
    client.stop();
    const rejection = expect(request).rejects.toThrow(/expired/);
    resolve(response(activeDisplay()));
    await rejection;
    await expect(client.displayFrame(identity.session_id, identity.generation)).rejects.toThrow(/ownership/);
    expect(transport.mock.calls.filter(([path]) => path === '/api/live/sessions')).toHaveLength(1);
    expect(transport.mock.calls.filter(([path]) => String(path).endsWith('/stop'))).toHaveLength(1);
    expect(onSnapshot).toHaveBeenCalledOnce();
  });

  it('exposes 429 backpressure without Stop, acquisition, or loss of the existing owner', async () => {
    let count = 0;
    const { client, transport, onNeutral } = setup(async () => ++count === 1
      ? response({ detail: 'Display client limit reached.' }, 429) : response(activeDisplay()));
    await client.start(fixture('SessionConfig'));
    await expect(client.displayFrame(identity.session_id, identity.generation)).rejects.toBeInstanceOf(DisplayBackpressureError);
    expect((await client.displayFrame(identity.session_id, identity.generation)).latest).not.toBeNull();
    expect(onNeutral).not.toHaveBeenCalled();
    expect(transport.mock.calls.filter(([path]) => path === '/api/live/sessions')).toHaveLength(1);
    expect(transport.mock.calls.filter(([path]) => String(path).endsWith('/stop'))).toHaveLength(0);
  });

  it('retries 429 in the mounted UI while the inspector is collapsed, without restarting or stopping', async () => {
    const snapshot = activeSnapshot();
    snapshot.kind = 'preview'; snapshot.model_mode = 'none'; snapshot.neural_sample = null;
    snapshot.last_inferred = null; snapshot.flight = null; snapshot.completed_calls = 0;
    snapshot.status.attempted_calls = 0; snapshot.status.state = 'previewing';
    const source = fixture('SourceList').sources[0];
    let displayRequests = 0;
    const fetcher = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit) => {
      const path = String(input);
      if (path.endsWith('/display')) {
        displayRequests++;
        if (displayRequests === 1) return response({ detail: 'Display busy.' }, 429);
        return response({ ...activeDisplay(), status: snapshot.status });
      }
      const value = path === '/health/live' ? fixture('LiveHealth')
        : path === '/api/live/config' ? fixture('LiveConfig')
          : path === '/api/live/control' ? fixture('ControlBootstrap')
            : path === '/api/live/sources' ? fixture('SourceList')
              : path === '/api/live/sources/inspect' ? source
                : path === '/api/live/status' ? { schema_version: 'obs-service-status-1', current: null }
                  : snapshot;
      return response(value);
    });
    vi.stubGlobal('fetch', fetcher);
    vi.stubGlobal('EventSource', class extends FixtureStream {});
    vi.stubGlobal('URL', class extends URL {
      static createObjectURL = vi.fn(() => 'blob:safe-fixture');
      static revokeObjectURL = vi.fn();
    });
    render(createElement(Live));
    await screen.findByText('Idle · local service available');
    fireEvent.click(screen.getByRole('button', { name: 'Live source' }));
    fireEvent.change(screen.getByLabelText('Source'), { target: { value: source.source_id } });
    expect(screen.getByLabelText('Inspect input')).not.toBeChecked();
    fireEvent.click(screen.getByRole('button', { name: 'Preview source' }));
    await waitFor(() => expect(displayRequests).toBeGreaterThanOrEqual(2));
    await waitFor(() => expect(screen.getByTestId('safe-fixture-stage')).toHaveAttribute('data-backdrop', 'blob:safe-fixture'));
    expect(fetcher.mock.calls.filter(([path]) => path === '/api/live/preview')).toHaveLength(1);
    expect(fetcher.mock.calls.filter(([path]) => path === '/api/live/sessions')).toHaveLength(0);
    expect(fetcher.mock.calls.filter(([path]) => String(path).endsWith('/stop'))).toHaveLength(0);
  });
});
