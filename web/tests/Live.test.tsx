import { StrictMode } from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Live, SourceThumbnail } from '../src/live/Live';
import examples from '../src/live/generated/examples.json';
import recorded from './fixtures/recorded-flight.json';
import { parseLiveContract, type ApiSnapshot, type ContractName, type LiveContracts } from '../src/live/contracts';

const graphics = vi.hoisted(() => ({ create: vi.fn() }));
vi.mock('../src/live/flightRenderer', () => ({ createFlightRenderer: graphics.create, FlightGraphicsError: class extends Error {} }));
function sample<K extends ContractName>(name: K): LiveContracts[K] {
  return parseLiveContract(name, examples.find(example => example.contract === name && example.valid)!.value);
}
class Stream extends EventTarget { close = vi.fn(); }
let stream: Stream;
let current: ApiSnapshot;
let source = sample('SourceList').sources[0];
function mockReads() {
  const fetcher = vi.fn().mockImplementation(async (path: string, init?: RequestInit) => {
    let value: unknown;
    if (path === '/health/live') value = sample('LiveHealth');
    else if (path === '/api/live/capabilities') value = { schema_version: 'obs-capabilities-1', profile: 'live', preview: true, inference: true, replay: true };
    else if (path === '/api/live/config') value = sample('LiveConfig');
    else if (path === '/api/live/control') value = sample('ControlBootstrap');
    else if (path === '/api/live/sources') value = { schema_version: 'obs-sources-1', sources: [source] };
    else if (path === '/api/live/status') value = { schema_version: 'obs-service-status-1', current: null };
    else if (path === '/api/live/sources/inspect') value = source;
    else if (path === '/api/live/sessions' || path === '/api/live/preview') {
      current.kind = path.endsWith('/preview') ? 'preview' : 'session';
      current.status.state = current.kind === 'preview' ? 'previewing' : 'running';
      if (current.kind === 'preview') { current.model_mode = 'none'; current.neural_sample = null; current.last_inferred = null; current.flight = null; current.completed_calls = 0; current.model_hz = 0; current.recording_state = 'off'; current.recording_id = null; }
      value = current;
    } else if (path.endsWith('/display')) {
      value = { schema_version: 'screen-gremlin-display-reply-1', status: current.status, latest: null };
    } else if (path.endsWith('/preview')) {
      const preview = sample('PreviewReply'); preview.status = current.status; preview.latest!.frame.sequence = 99;
      preview.latest!.observation_u8.fill(200); value = preview;
    } else if (path === '/api/live/replays') value = { schema_version: 'obs-replay-list-1', recordings: [] };
    else if (path.includes('/sessions/')) value = current;
    else throw new Error(`Unexpected request ${path} ${init?.method}`);
    return new Response(JSON.stringify(value), { status: 200 });
  });
  vi.stubGlobal('fetch', fetcher);
  return fetcher;
}
async function enterLive() {
  await screen.findByText('Idle · local service available');
  fireEvent.click(screen.getByRole('button', { name: 'Live source' }));
  fireEvent.change(screen.getByLabelText('Source'), { target: { value: source.source_id } });
  await waitFor(() => expect(screen.getByTestId('graphics-state')).toHaveTextContent('Ready'));
}
beforeEach(() => {
  graphics.create.mockReset().mockImplementation(() => ({ draw: vi.fn(), resize: vi.fn(), dispose: vi.fn() }));
  stream = new Stream(); vi.stubGlobal('EventSource', function () { return stream; });
  source = sample('SourceList').sources[0]; current = sample('ApiSnapshot');
  current.kind = 'session'; current.status.state = 'running'; current.lease_remaining_ms = 3000;
  current.model_mode = 'real'; current.capture_hz = 30; current.model_hz = 2;
  current.last_inferred = current.neural_sample;
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation(() => ({ createImageData: (width: number, height: number) => ({ data: new Uint8ClampedArray(width * height * 4), width, height }), putImageData: vi.fn(), clearRect: vi.fn() } as unknown as CanvasRenderingContext2D));
  Object.defineProperty(document, 'hidden', { configurable: true, value: false });
});

describe('OBS05 operator session page', () => {
  it('starts idle with passive reads, explicit source selection and default-off recording', async () => {
    const fetcher = mockReads(); render(<Live />);
    await enterLive();
    expect(screen.getByLabelText('Record this session locally')).not.toBeChecked();
    expect(screen.getByRole('button', { name: 'Start live flight' })).toBeEnabled();
    expect(fetcher.mock.calls.map(call => call[0])).toEqual(['/health/live', '/api/live/config', '/api/live/sources', '/api/live/status', '/api/live/capabilities']);
    expect(fetcher.mock.calls.every(call => !call[1]?.method || call[1].method === 'GET')).toBe(true);
  });
  it('requires a selected source before Preview or Start and supports keyboard mode selection', async () => {
    mockReads(); render(<Live />); await screen.findByText('Idle · local service available');
    const user = userEvent.setup(); screen.getByRole('button', { name: 'Live source' }).focus(); await user.keyboard('{Enter}');
    expect(screen.getByRole('button', { name: 'Start live flight' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Preview source' })).toBeDisabled();
    expect(screen.getByLabelText('Source')).toHaveValue('');
  });
  it('previews explicitly without a neural Start and stops on tab hiding', async () => {
    const fetcher = mockReads(); render(<Live />); await enterLive();
    fireEvent.click(screen.getByRole('button', { name: 'Preview source' }));
    await waitFor(() => expect(screen.getByTestId('session-status')).toHaveTextContent('previewing'));
    expect(screen.getByText('CAPTURE-ONLY PREVIEW')).toBeInTheDocument();
    expect(fetcher.mock.calls.some(call => call[0] === '/api/live/sessions')).toBe(false);
    Object.defineProperty(document, 'hidden', { configurable: true, value: true }); fireEvent(document, new Event('visibilitychange'));
    await waitFor(() => expect(fetcher.mock.calls.some(call => call[0].endsWith('/stop'))).toBe(true));
    Object.defineProperty(document, 'hidden', { configurable: true, value: false }); fireEvent(document, new Event('visibilitychange'));
    expect(fetcher.mock.calls.filter(call => call[0] === '/api/live/preview')).toHaveLength(1);
  });
  it('displays distinct newest input and exact neural bytes, rates and source identities', async () => {
    mockReads(); render(<Live />); await enterLive();
    fireEvent.click(screen.getByLabelText('Inspect input'));
    fireEvent.click(screen.getByRole('button', { name: 'Start live flight' }));
    await waitFor(() => expect(screen.getByTestId('source-preview-id')).toHaveTextContent('99'));
    expect(JSON.parse(screen.getByTestId('source-preview-bytes').textContent!)).toEqual(Array(256).fill(200));
    expect(JSON.parse(screen.getByTestId('inferred-input-bytes').textContent!)).toEqual(current.last_inferred!.observation_u8);
    expect(JSON.parse(screen.getByTestId('neural-values').textContent!)).toEqual(current.last_inferred!.motor_rates_hz);
    expect(screen.getByTestId('inferred-input-id')).toHaveTextContent('fixture-source');
    expect(screen.getByTestId('capture-hz')).toHaveTextContent('30.0 Hz');
    expect(screen.getByTestId('neural-hz')).toHaveTextContent('2.00 Hz');
    expect(screen.getByTestId('model-mode')).toHaveTextContent('Actual neural model');
    expect(screen.getByText('NEURAL-DRIVEN LIVE FLIGHT')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Session details & input inspector'));
    const squares = screen.getByRole('img', { name: 'Exact input used for displayed neural response' }).querySelectorAll('rect');
    current.last_inferred!.observation_u8.forEach((value, index) => expect(squares[index]).toHaveAttribute('fill', `rgb(${value},${value},${value})`));
  });
  it('keeps the monitor recording checkbox disabled and sends bounded config without execution purpose', async () => {
    source = { ...source, source_id: 'v4l2-video0', evidence_kind: 'real', backend: 'ffmpeg-v4l2', producer_detection: 'obs_readonly_monitor' };
    const fetcher = mockReads(); render(<Live />); await enterLive();
    expect(screen.getByLabelText('Record this session locally')).toBeDisabled();
    fireEvent.change(screen.getByLabelText('Maximum model calls'), { target: { value: '2' } });
    fireEvent.change(screen.getByLabelText('Seed'), { target: { value: '17' } });
    fireEvent.click(screen.getByRole('button', { name: 'Start live flight' }));
    await waitFor(() => expect(fetcher.mock.calls.some(call => call[0] === '/api/live/sessions')).toBe(true));
    const body = JSON.parse(fetcher.mock.calls.find(call => call[0] === '/api/live/sessions')![1].body);
    expect(body.config).toMatchObject({ max_model_calls: 2, seed: 17, recording: false });
    expect(body.recording_consent).toBe(false); expect(body.config).not.toHaveProperty('purpose'); expect(body).not.toHaveProperty('purpose');
  });
  it('neutralizes disconnected sessions, ignores late events, and never fetches synthetic fallback', async () => {
    const fetcher = mockReads(); render(<Live />); await enterLive();
    fireEvent.click(screen.getByLabelText('Inspect input')); fireEvent.click(screen.getByRole('button', { name: 'Start live flight' }));
    await waitFor(() => expect(screen.getByTestId('session-status')).toHaveTextContent('running'));
    const oldPose = screen.getByTestId('authoritative-pose').textContent;
    act(() => stream.dispatchEvent(new Event('error')));
    expect(screen.getByTestId('session-status')).toHaveTextContent('connection lost');
    const foreign = structuredClone(current); foreign.event_sequence += 10; foreign.flight!.position = [100, 100, 100];
    act(() => stream.dispatchEvent(new MessageEvent('snapshot', { data: JSON.stringify(foreign) })));
    expect(screen.getByTestId('authoritative-pose').textContent).toBe(oldPose);
    expect(fetcher.mock.calls.some(call => call[0].includes('flight-preview'))).toBe(false);
    expect(screen.getByRole('button', { name: 'Start live flight' })).toBeEnabled();
  });
  it('releases session ownership on graphics failure and does not resume on Retry', async () => {
    const fetcher = mockReads(); render(<Live />); await enterLive();
    fireEvent.click(screen.getByRole('button', { name: 'Start live flight' }));
    await waitFor(() => expect(screen.getByTestId('session-status')).toHaveTextContent('running'));
    act(() => graphics.create.mock.calls.at(-1)![1](new Error('GPU lost')));
    await waitFor(() => expect(fetcher.mock.calls.some(call => call[0].endsWith('/stop'))).toBe(true));
    expect(screen.getByRole('button', { name: 'Start live flight' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Retry graphics' }));
    expect(fetcher.mock.calls.filter(call => call[0] === '/api/live/sessions')).toHaveLength(1);
  });
  it('opens recording listing without capture or inference', async () => {
    const fetcher = mockReads(); render(<Live />); await screen.findByText('Idle · local service available');
    fireEvent.click(screen.getByRole('button', { name: 'Recorded playback' }));
    await waitFor(() => expect(fetcher.mock.calls.some(call => call[0] === '/api/live/replays')).toBe(true));
    expect(screen.getByText('RECORDED PLAYBACK')).toBeInTheDocument();
    expect(fetcher.mock.calls.every(call => !call[1]?.method || call[1].method === 'GET')).toBe(true);
  });
  it.each(['/health/live', '/api/live/config', '/api/live/sources', '/api/live/status', '/api/live/capabilities'])('rejects invalid %s responses', async badPath => {
    const fetcher = mockReads(); const original = fetcher.getMockImplementation()!;
    fetcher.mockImplementation((path, init) => path === badPath ? Promise.resolve(new Response('{"invented":true}')) : original(path, init));
    render(<Live />); expect(await screen.findByRole('alert')).toHaveTextContent('Invalid live');
    expect(screen.queryByText('Idle · local service available')).not.toBeInTheDocument();
  });
  it('remains read-only across StrictMode cleanup and remount', async () => {
    const fetcher = mockReads(); const view = render(<StrictMode><Live /></StrictMode>);
    await screen.findByText('Idle · local service available');
    expect(fetcher.mock.calls).toHaveLength(10);
    expect(fetcher.mock.calls.every(call => !call[1]?.method || call[1].method === 'GET')).toBe(true);
    view.unmount();
    for (const call of fetcher.mock.calls.filter(call => call[1]?.signal)) expect(call[1].signal.aborted).toBe(true);
  });
});


it('cancels pending source inspection on mode change and permits a fresh explicit action', async () => {
  const fetcher = mockReads(); const original = fetcher.getMockImplementation()!;
  let resolveInspection: (value: Response) => void = () => {};
  fetcher.mockImplementation((path, init) => path.endsWith('/sources/inspect') ? new Promise<Response>(resolve => { resolveInspection = resolve; }) : original(path, init));
  render(<Live />); await enterLive(); fireEvent.click(screen.getByRole('button', { name: 'Preview source' }));
  await waitFor(() => expect(fetcher.mock.calls.some(call => call[0].endsWith('/sources/inspect'))).toBe(true));
  fireEvent.click(screen.getByRole('button', { name: 'Synthetic demonstration' }));
  await act(async () => { resolveInspection(new Response(JSON.stringify(source))); });
  fireEvent.click(screen.getByRole('button', { name: 'Live source' }));
  expect(screen.getByRole('button', { name: 'Preview source' })).toBeEnabled();
  expect(fetcher.mock.calls.some(call => call[0] === '/api/live/preview' || call[0] === '/api/live/sessions')).toBe(false);
});

it('validates numeric bounds before inspecting or opening the source', async () => {
  const fetcher = mockReads(); render(<Live />); await enterLive();
  fireEvent.change(screen.getByLabelText('Maximum model calls'), { target: { value: '513' } });
  fireEvent.click(screen.getByRole('button', { name: 'Start live flight' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('1 to 512 model calls');
  expect(fetcher.mock.calls.some(call => call[0].endsWith('/sources/inspect'))).toBe(false);
});


it('shows a previous failure and reason after reload without taking ownership', async () => {
  const fetcher = mockReads(); const original = fetcher.getMockImplementation()!;
  current.status.state = 'failed'; current.status.reason = 'Source receipt deadline exceeded.';
  fetcher.mockImplementation((path, init) => path === '/api/live/status' ? Promise.resolve(new Response(JSON.stringify({ schema_version: 'obs-service-status-1', current }))) : original(path, init));
  render(<Live />);
  await waitFor(() => expect(screen.getByTestId('session-status')).toHaveTextContent('Existing session · failed · Source receipt deadline exceeded.'));
  expect(fetcher.mock.calls.every(call => !call[1]?.method || call[1].method === 'GET')).toBe(true);
});


async function loadDownloadFixture(pending = false) {
  const payload = structuredClone(recorded);
  for (const sample of payload.samples) sample.raw_action.dy = -0;
  for (const result of payload.results) { result.raw_action.dy = -0; result.output.dy = -0; }
  const text = JSON.stringify(payload).replaceAll('"dy":0', '"dy":-0.0');
  const id = 'f'.repeat(32);
  const fetcher = mockReads(); const original = fetcher.getMockImplementation()!;
  let resolveDownload: (response: Response) => void = () => {};
  fetcher.mockImplementation((path, init) => {
    if (path === '/api/live/replays') return Promise.resolve(new Response(JSON.stringify({ schema_version: 'obs-replay-list-1', recordings: [{ recording_id: id, manifest: payload.manifest }] })));
    if (path.endsWith('/download') && pending) return new Promise<Response>(resolve => { resolveDownload = resolve; });
    if (path.startsWith(`/api/live/replays/${id}`)) return Promise.resolve(new Response(text));
    return original(path, init);
  });
  const create = vi.fn((_blob: Blob) => 'blob:local-recording'); const revoke = vi.fn();
  vi.stubGlobal('URL', class extends URL { static createObjectURL = create; static revokeObjectURL = revoke; });
  const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
  render(<Live />); await screen.findByText('Idle · local service available');
  fireEvent.click(screen.getByRole('button', { name: 'Recorded playback' }));
  await screen.findByRole('option', { name: `${id} · complete` });
  fireEvent.change(screen.getByLabelText('Recording'), { target: { value: id } });
  fireEvent.click(screen.getByRole('button', { name: 'Load recording' }));
  await screen.findByTestId('loaded-recording-id');
  return { text, id, fetcher, create, click, resolveDownload: () => resolveDownload(new Response(text)) };
}

it('downloads the original validated recording bytes preserving negative zero and loaded identity', async () => {
  const { text, id, fetcher, create, click } = await loadDownloadFixture();
  fireEvent.click(screen.getByRole('button', { name: 'Download recording' }));
  await waitFor(() => expect(create).toHaveBeenCalledTimes(1));
  const blob = create.mock.calls[0][0] as Blob;
  const downloaded = await new Promise<string>((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result as string); reader.onerror = reject; reader.readAsText(blob); });
  expect(downloaded).toBe(text); expect(downloaded).toContain('"dy":-0.0');
  expect(Object.is(JSON.parse(downloaded).results[0].raw_action.dy, -0)).toBe(true);
  expect((click.mock.instances[0] as HTMLAnchorElement).download).toBe(`${id}.json`);
  expect(fetcher.mock.calls.some(call => call[0] === `/api/live/replays/${id}/download`)).toBe(true);
  expect(fetcher.mock.calls.every(call => !call[1]?.method || call[1].method === 'GET')).toBe(true);
});

it('discards a pending recording download after the operator changes modes', async () => {
  const { fetcher, create, resolveDownload } = await loadDownloadFixture(true);
  fireEvent.click(screen.getByRole('button', { name: 'Download recording' }));
  await waitFor(() => expect(fetcher.mock.calls.some(call => call[0].endsWith('/download'))).toBe(true));
  fireEvent.click(screen.getByRole('button', { name: 'Synthetic demonstration' }));
  await act(async () => resolveDownload());
  expect(create).not.toHaveBeenCalled();
});


it('draws validated RGB thumbnail bytes exactly and clears the ephemeral canvas on replacement and unmount', () => {
  const context = { createImageData: (width: number, height: number) => ({ data: new Uint8ClampedArray(width * height * 4), width, height }), putImageData: vi.fn(), clearRect: vi.fn() };
  vi.mocked(HTMLCanvasElement.prototype.getContext).mockReturnValue(context as unknown as CanvasRenderingContext2D);
  const source = parseLiveContract('SourcePreview', { ...sample('PreviewReply').latest!, width: 2, height: 1, rgb_base64: btoa(String.fromCharCode(9, 128, 255, 240, 32, 1)) });
  const view = render(<SourceThumbnail source={source} />);
  expect(screen.getByRole('img', { name: 'Newest source RGB thumbnail' })).toHaveAttribute('width', '2');
  expect(Array.from(context.putImageData.mock.calls[0][0].data)).toEqual([9, 128, 255, 255, 240, 32, 1, 255]);
  const next = { ...source, frame: { ...source.frame, sequence: source.frame.sequence + 1 }, rgb_base64: btoa(String.fromCharCode(2, 4, 6, 8, 10, 12)) };
  view.rerender(<SourceThumbnail source={next} />);
  expect(context.clearRect).toHaveBeenCalledTimes(1);
  expect(Array.from(context.putImageData.mock.calls[1][0].data)).toEqual([2, 4, 6, 255, 8, 10, 12, 255]);
  view.unmount(); expect(context.clearRect).toHaveBeenCalledTimes(2);
});

it('delivers the owned backdrop with inspectors collapsed and releases every image URL on Stop', async () => {
  const fetcher = mockReads(); const original = fetcher.getMockImplementation()!;
  const packet = sample('DisplayReply'); packet.status = current.status;
  packet.latest!.frame.source_id = source.source_id;
  const create = vi.fn(() => 'blob:ephemeral-source'); const revoke = vi.fn();
  vi.stubGlobal('URL', class extends URL { static createObjectURL = create; static revokeObjectURL = revoke; });
  fetcher.mockImplementation((path, init) => path.endsWith('/display') ? Promise.resolve(new Response(JSON.stringify(packet))) : original(path, init));
  const view = render(<Live />); await enterLive();
  expect(screen.getByLabelText('Inspect input')).not.toBeChecked();
  fireEvent.click(screen.getByRole('button', { name: 'Start live flight' }));
  const image = await screen.findByRole('img', { name: 'Selected source presentation frame' });
  expect(image).toHaveAttribute('src', 'blob:ephemeral-source');
  expect(fetcher.mock.calls.some(call => call[0].endsWith('/display'))).toBe(true);
  expect(fetcher.mock.calls.filter(call => call[0].includes('/sessions/') && call[0].endsWith('/preview'))).toHaveLength(0);
  fireEvent.click(screen.getByRole('button', { name: 'Stop session' }));
  await waitFor(() => expect(screen.queryByRole('img', { name: 'Selected source presentation frame' })).not.toBeInTheDocument());
  expect(revoke).toHaveBeenCalledWith('blob:ephemeral-source');
  view.unmount(); expect(create.mock.calls.length).toBe(revoke.mock.calls.length);
});

it('discards pending display frames after a source mode change without showing synthetic content in live mode', async () => {
  const fetcher = mockReads(); const original = fetcher.getMockImplementation()!;
  let resolveDisplay: (response: Response) => void = () => {};
  fetcher.mockImplementation((path, init) => path.endsWith('/display') ? new Promise<Response>(resolve => { resolveDisplay = resolve; }) : original(path, init));
  const create = vi.fn(() => 'blob:late');
  vi.stubGlobal('URL', class extends URL { static createObjectURL = create; static revokeObjectURL = vi.fn(); });
  render(<Live />); await enterLive(); fireEvent.click(screen.getByRole('button', { name: 'Start live flight' }));
  await waitFor(() => expect(fetcher.mock.calls.some(call => call[0].endsWith('/display'))).toBe(true));
  fireEvent.click(screen.getByRole('button', { name: 'Recorded playback' }));
  await act(async () => resolveDisplay(new Response(JSON.stringify(sample('DisplayReply')))));
  expect(create).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button', { name: 'Live source' }));
  expect(screen.getByTestId('screen-backdrop').querySelector('img')).toBeNull();
});

it('explains art review before any click, disables neural controls, and keeps Preview and replay available', async () => {
  const fetcher = mockReads(); const original = fetcher.getMockImplementation()!;
  fetcher.mockImplementation((path, init) => path === '/api/live/capabilities' ? Promise.resolve(new Response(JSON.stringify({
    schema_version: 'obs-capabilities-1', profile: 'art_review', preview: true, inference: false, replay: true,
  }))) : original(path, init));
  render(<Live />); await enterLive();
  expect(screen.getByTestId('launch-profile')).toHaveTextContent('Art review — capture-only demo and saved replays.');
  const start = screen.getByRole('button', { name: 'Start live flight' });
  expect(start).toBeDisabled();
  expect(start).toHaveAccessibleDescription(/Run .\/scripts\/dev_sg01_live.sh/);
  expect(screen.getByLabelText('Maximum model calls')).toBeDisabled();
  expect(screen.getByLabelText('Record this session locally')).toBeDisabled();
  expect(screen.getByRole('button', { name: 'Preview source' })).toBeEnabled();
  expect(screen.getByRole('button', { name: 'Recorded playback' })).toBeEnabled();
  fireEvent.click(start);
  expect(fetcher.mock.calls.every(call => !call[1]?.method || call[1].method === 'GET')).toBe(true);
  fireEvent.click(screen.getByRole('button', { name: 'Preview source' }));
  await waitFor(() => expect(screen.getByTestId('session-status')).toHaveTextContent('previewing'));
  expect(fetcher.mock.calls.some(call => call[0] === '/api/live/sessions')).toBe(false);
});

it('keeps safe synthetic source inference available when the server supports it', async () => {
  const fetcher = mockReads(); render(<Live />); await enterLive();
  expect(source.backend).toBe('synthetic');
  fireEvent.click(screen.getByRole('button', { name: 'Start live flight' }));
  await waitFor(() => expect(fetcher.mock.calls.some(call => call[0] === '/api/live/sessions')).toBe(true));
});
