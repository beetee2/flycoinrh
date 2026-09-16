import { StrictMode } from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { FlightStage } from '../src/live/FlightStage';
import type { FlightSnapshot } from '../src/live/contracts';
import { FlightGraphicsError } from '../src/live/flightRenderer';

const mocks = vi.hoisted(() => ({ create: vi.fn(), draw: vi.fn(), dispose: vi.fn() }));
vi.mock('../src/live/flightRenderer', async importOriginal => ({ ...await importOriginal<typeof import('../src/live/flightRenderer')>(), createFlightRenderer: mocks.create }));
function fixture() {
  return { schema_version: 'obs-flight-preview-1', evidence_kind: 'synthetic', dt_ms: 20,
    snapshots: Array.from({ length: 101 }, (_, tick) => ({ schema_version: 'obs-flight-1', session_id: 'synthetic-preview',
      generation: 1, evidence_kind: 'fixture', tick, position: [tick, 0, 0], yaw_rad: tick * .01, pitch_rad: 0,
      speed_units_s: tick ? 1 : 0, applied_response_id: null, neutral: tick === 0 })) };
}
let frames: Map<number, FrameRequestCallback>;
let now: number;
function advance(ms: number) {
  now += ms;
  act(() => { const callbacks = [...frames.values()]; frames.clear(); callbacks.forEach(callback => callback(now)); });
}
async function load() {
  fireEvent.click(screen.getByRole('button', { name: 'Load synthetic preview' }));
  await screen.findByText('Loaded · idle');
}
beforeEach(() => {
  mocks.create.mockReset().mockImplementation(() => ({ draw: mocks.draw, resize: vi.fn(), dispose: mocks.dispose }));
  mocks.draw.mockReset(); mocks.dispose.mockClear();
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => fixture() }));
  frames = new Map(); now = 0; let id = 0;
  vi.spyOn(performance, 'now').mockImplementation(() => now);
  vi.stubGlobal('requestAnimationFrame', vi.fn((callback: FrameRequestCallback) => { frames.set(++id, callback); return id; }));
  vi.stubGlobal('cancelAnimationFrame', vi.fn((frame: number) => frames.delete(frame)));
});

describe('flight stage lifecycle', () => {
  it('loads only on demand, plays explicitly, and freezes pose on pause and Stop', async () => {
    render(<FlightStage />);
    expect(fetch).not.toHaveBeenCalled(); expect(frames.size).toBe(0);
    await load(); expect(fetch).toHaveBeenCalledTimes(1); expect(frames.size).toBe(0);
    expect(screen.getByTestId('flight-position')).toHaveTextContent('0.00 / 0.00 / 0.00');
    fireEvent.click(screen.getByRole('button', { name: 'Play synthetic preview' }));
    expect(frames.size).toBe(1); advance(200);
    expect(screen.getByTestId('flight-tick')).toHaveTextContent('10');
    const pose = screen.getByTestId('flight-position').textContent;
    fireEvent.click(screen.getByRole('button', { name: 'Pause' }));
    expect(frames.size).toBe(0); advance(1000); expect(screen.getByTestId('flight-position')).toHaveTextContent(pose!);
    fireEvent.click(screen.getByRole('button', { name: 'Play synthetic preview' })); advance(100);
    expect(screen.getByTestId('flight-tick')).toHaveTextContent('15');
    fireEvent.click(screen.getByRole('button', { name: 'Stop' }));
    expect(frames.size).toBe(0); expect(screen.getByTestId('preview-state')).toHaveTextContent('Stopped · frozen');
    const stopped = screen.getByTestId('flight-position').textContent; advance(1000);
    expect(screen.getByTestId('flight-position')).toHaveTextContent(stopped!);
    fireEvent.click(screen.getByRole('button', { name: 'Reset preview' }));
    expect(screen.getByTestId('flight-tick')).toHaveTextContent('0'); expect(frames.size).toBe(0);
  });
  it('pauses a hidden tab and does not automatically resume it', async () => {
    render(<FlightStage />); await load(); fireEvent.click(screen.getByRole('button', { name: 'Play synthetic preview' })); advance(100);
    Object.defineProperty(document, 'hidden', { configurable: true, value: true });
    fireEvent(document, new Event('visibilitychange')); expect(frames.size).toBe(0);
    const pose = screen.getByTestId('flight-position').textContent;
    Object.defineProperty(document, 'hidden', { configurable: true, value: false });
    fireEvent(document, new Event('visibilitychange')); advance(1000);
    expect(screen.getByTestId('flight-position')).toHaveTextContent(pose!); expect(frames.size).toBe(0);
  });
  it('ends at the final snapshot and requires reset before playing again', async () => {
    render(<FlightStage />); await load(); fireEvent.click(screen.getByRole('button', { name: 'Play synthetic preview' })); advance(5000);
    expect(screen.getByTestId('flight-tick')).toHaveTextContent('100'); expect(frames.size).toBe(0);
    expect(screen.getByRole('button', { name: 'Play synthetic preview' })).toBeDisabled();
    expect(screen.getByText('Complete · frozen')).toBeInTheDocument();
  });
  it('has one active loop across StrictMode remount and disposes graphics and requests on unmount', async () => {
    const view = render(<StrictMode><FlightStage /></StrictMode>);
    expect(mocks.create).toHaveBeenCalledTimes(2); expect(mocks.dispose).toHaveBeenCalledTimes(1);
    await load(); fireEvent.click(screen.getByRole('button', { name: 'Play synthetic preview' })); advance(40); expect(frames.size).toBe(1);
    const signal = vi.mocked(fetch).mock.calls[0][1]!.signal!;
    view.unmount(); expect(frames.size).toBe(0); expect(mocks.dispose).toHaveBeenCalledTimes(2); expect(signal.aborted).toBe(true);
  });
  it('reports unavailable WebGL without enabling playback', async () => {
    mocks.create.mockImplementation(() => { throw new Error('WebGL unavailable'); });
    render(<FlightStage />); expect(screen.getByText(/3D view unavailable\./)).toBeInTheDocument();
    await load(); expect(screen.getByRole('button', { name: 'Play synthetic preview' })).toBeDisabled(); expect(frames.size).toBe(0);
  });
  it('freezes immediately if the WebGL context is lost', async () => {
    render(<FlightStage />); await load(); fireEvent.click(screen.getByRole('button', { name: 'Play synthetic preview' })); advance(100);
    act(() => mocks.create.mock.calls.at(-1)![1](new FlightGraphicsError('context-lost', 'GPU context lost')));
    expect(frames.size).toBe(0); expect(screen.getByRole('button', { name: 'Play synthetic preview' })).toBeDisabled();
  });
  it('keeps sanitized context diagnostics and data readiness after a successful explicit retry', async () => {
    mocks.create.mockImplementationOnce(() => { throw new FlightGraphicsError('context-creation', 'BindToCurrentSequence failed\n/home/private/profile https://private.test/token'); });
    render(<FlightStage />); await load();
    expect(screen.getByTestId('graphics-state')).toHaveTextContent('Context creation failed');
    expect(screen.getByTestId('preview-data-state')).toHaveTextContent('Loaded');
    expect(screen.getByTestId('graphics-details')).toHaveTextContent('BindToCurrentSequence failed [path] [URL]');
    fireEvent.click(screen.getByRole('button', { name: 'Retry graphics' }));
    expect(mocks.create).toHaveBeenCalledTimes(2);
    expect(screen.getByTestId('graphics-state')).toHaveTextContent('Ready');
    expect(screen.getByTestId('graphics-details')).toHaveTextContent('BindToCurrentSequence failed');
    expect(screen.getByRole('button', { name: 'Play synthetic preview' })).toBeEnabled();
    expect(frames.size).toBe(0);
    expect(fetch).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole('button', { name: 'Play synthetic preview' })); advance(40);
    expect(mocks.draw.mock.calls.at(-1)![0].tick).toBe(2);
  });
  it('bounds failed retries and never retries on data load, reset, or time advancement', async () => {
    mocks.create.mockImplementation(() => { throw new FlightGraphicsError('renderer', 'Scene allocation failed'); });
    render(<FlightStage />); await load();
    expect(screen.getByTestId('graphics-state')).toHaveTextContent('Renderer failed');
    for (let count = 0; count < 5; count++) fireEvent.click(screen.getByRole('button', { name: 'Retry graphics' }));
    expect(mocks.create).toHaveBeenCalledTimes(4);
    expect(screen.getByLabelText('Presentation')).toBeDisabled();
    fireEvent.change(screen.getByLabelText('Presentation'), { target: { value: 'legacy' } });
    expect(mocks.create).toHaveBeenCalledTimes(4);
    expect(screen.getByRole('button', { name: 'Retry graphics' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Reset preview' })); advance(2000); await load();
    expect(mocks.create).toHaveBeenCalledTimes(4);
    expect(frames.size).toBe(0);
    expect(screen.getByRole('button', { name: 'Play synthetic preview' })).toBeDisabled();
  });
  it('disposes a lost renderer, preserves the frozen pose through retry, and ignores late callbacks after unmount', async () => {
    const view = render(<FlightStage />); await load();
    fireEvent.click(screen.getByRole('button', { name: 'Play synthetic preview' })); advance(100);
    const lost = mocks.create.mock.calls.at(-1)![1];
    act(() => lost(new FlightGraphicsError('context-lost', 'Context lost')));
    expect(mocks.dispose).toHaveBeenCalledTimes(1); expect(frames.size).toBe(0);
    expect(screen.getByTestId('preview-state')).toHaveTextContent('Paused · graphics unavailable');
    fireEvent.click(screen.getByRole('button', { name: 'Retry graphics' }));
    expect(mocks.draw.mock.calls.at(-1)![0].tick).toBe(5);
    advance(1000); expect(frames.size).toBe(0);
    expect(screen.getByTestId('flight-tick')).toHaveTextContent('5');
    expect(screen.getByTestId('preview-state')).toHaveTextContent('Paused · graphics restored');
    view.unmount(); expect(mocks.dispose).toHaveBeenCalledTimes(2);
    act(() => lost(new FlightGraphicsError('context-lost', 'Late event')));
    render(<FlightStage />);
    expect(screen.getByTestId('graphics-state')).toHaveTextContent('Ready');
    expect(screen.queryByTestId('graphics-details')).not.toBeInTheDocument();
  });
  it('stops the loop and releases graphics when drawing throws', async () => {
    render(<FlightStage />); await load();
    fireEvent.click(screen.getByRole('button', { name: 'Play synthetic preview' }));
    mocks.draw.mockImplementationOnce(() => { throw new Error('Render failed'); }); advance(40);
    expect(screen.getByTestId('graphics-state')).toHaveTextContent('Renderer failed');
    expect(frames.size).toBe(0); expect(mocks.dispose).toHaveBeenCalledTimes(1);
    expect(screen.getByRole('button', { name: 'Play synthetic preview' })).toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Retry graphics' }));
    expect(mocks.draw.mock.calls.at(-1)![0].tick).toBe(0);
    expect(screen.getByTestId('flight-tick')).toHaveTextContent('0');
    expect(screen.getByTestId('preview-state')).toHaveTextContent('Paused · graphics restored');
    expect(frames.size).toBe(0);
  });
  it.each(['invalid', 'transport', 'http'])('rejects %s preview and never begins playback', async kind => {
    if (kind === 'invalid') vi.mocked(fetch).mockResolvedValue({ ok: true, json: async () => ({ ...fixture(), evidence_kind: 'real' }) } as Response);
    if (kind === 'transport') vi.mocked(fetch).mockRejectedValue(new Error('Disconnected'));
    if (kind === 'http') vi.mocked(fetch).mockResolvedValue({ ok: false, status: 503 } as Response);
    render(<FlightStage />); fireEvent.click(screen.getByRole('button', { name: 'Load synthetic preview' }));
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
    expect(screen.getByRole('button', { name: 'Play synthetic preview' })).toBeDisabled(); expect(frames.size).toBe(0);
  });
});


describe('authoritative live presentation', () => {
  const pose = (tick: number): FlightSnapshot => ({ schema_version: 'obs-flight-1', session_id: 'live-session', generation: 1,
    evidence_kind: 'fixture', tick, position: [tick, 0, 0], yaw_rad: 0, pitch_rad: 0, speed_units_s: 1,
    applied_response_id: 'response-1', neutral: false });
  it('interpolates between server poses for at most 100 ms without prediction', () => {
    const view = render(<FlightStage mode="live" snapshot={pose(0)} motionAllowed />);
    view.rerender(<FlightStage mode="live" snapshot={pose(10)} motionAllowed />);
    expect(frames.size).toBe(1); advance(50);
    expect(mocks.draw.mock.calls.at(-1)![0].position).toEqual([5, 0, 0]);
    advance(50); expect(mocks.draw.mock.calls.at(-1)![0]).toEqual(pose(10)); expect(frames.size).toBe(0);
    advance(2000); expect(mocks.draw.mock.calls.at(-1)![0]).toEqual(pose(10)); expect(fetch).not.toHaveBeenCalled();
  });
  it('freezes transport loss at the last rendered pose immediately and accepts a final neutral pose', () => {
    const end = pose(10); const view = render(<FlightStage mode="live" snapshot={pose(0)} motionAllowed />);
    view.rerender(<FlightStage mode="live" snapshot={end} motionAllowed />); advance(50);
    view.rerender(<FlightStage mode="live" snapshot={end} motionAllowed={false} />);
    expect(frames.size).toBe(0); advance(3000);
    expect(mocks.draw.mock.calls.at(-1)![0].position).toEqual([5, 0, 0]);
    const terminal = { ...end, neutral: true, speed_units_s: 0 };
    view.rerender(<FlightStage mode="live" snapshot={terminal} motionAllowed={false} />);
    expect(mocks.draw.mock.calls.at(-1)![0]).toEqual(terminal);
  });
  it('renders replay seeks exactly while paused without starting any source or animation loop', () => {
    const view = render(<FlightStage mode="replay" snapshot={pose(10)} />);
    view.rerender(<FlightStage mode="replay" snapshot={pose(2)} />);
    expect(mocks.draw.mock.calls.at(-1)![0]).toEqual(pose(2)); expect(frames.size).toBe(0); expect(fetch).not.toHaveBeenCalled();
    view.unmount(); expect(mocks.dispose).toHaveBeenCalledTimes(1);
  });
});


it('keeps locally released flight frozen through later terminal packets and graphics Retry', () => {
  const first: FlightSnapshot = { schema_version: 'obs-flight-1', session_id: 'released-session', generation: 1,
    evidence_kind: 'fixture', tick: 1, position: [1, 0, 0], yaw_rad: 0, pitch_rad: 0, speed_units_s: 1,
    applied_response_id: 'response-1', neutral: false };
  const view = render(<FlightStage mode="live" snapshot={first} motionAllowed />);
  const terminal: FlightSnapshot = { ...first, tick: 50, position: [2, 0, 0], speed_units_s: 0, neutral: true };
  view.rerender(<FlightStage mode="live" snapshot={terminal} freezePose />);
  advance(4000); expect(mocks.draw.mock.calls.at(-1)![0]).toEqual(first); expect(frames.size).toBe(0);
  act(() => mocks.create.mock.calls.at(-1)![1](new FlightGraphicsError('context-lost', 'Lost')));
  fireEvent.click(screen.getByRole('button', { name: 'Retry graphics' }));
  expect(mocks.draw.mock.calls.at(-1)![0]).toEqual(first); expect(frames.size).toBe(0);
});


it('reports measured render calls separately from neural updates and returns to zero while idle', () => {
  vi.useFakeTimers();
  try {
    const rate = vi.fn(); const view = render(<FlightStage onRenderingRate={rate} />);
    const drawn = mocks.draw.mock.calls.length;
    now = 500; act(() => vi.advanceTimersByTime(500)); expect(rate).toHaveBeenLastCalledWith(drawn * 2);
    now = 1000; act(() => vi.advanceTimersByTime(500)); expect(rate).toHaveBeenLastCalledWith(0);
    view.unmount(); expect(vi.getTimerCount()).toBe(0);
  } finally { vi.useRealTimers(); }
});

it('keeps authoritative poses identical across view, caption, and background changes with no control request', () => {
  const snapshot = fixture().snapshots[25] as FlightSnapshot;
  render(<FlightStage mode="replay" snapshot={snapshot} />);
  expect(mocks.draw.mock.calls.at(-1)![0]).toEqual(snapshot);
  fireEvent.change(screen.getByLabelText('Presentation'), { target: { value: 'legacy' } });
  expect(mocks.draw.mock.calls.at(-1)![0]).toEqual(snapshot);
  fireEvent.change(screen.getByLabelText('Presentation'), { target: { value: 'screen-gremlin' } });
  expect(mocks.draw.mock.calls.at(-1)![0]).toEqual(snapshot);
  fireEvent.change(screen.getByLabelText('Caption'), { target: { value: '<img src=x onerror=alert(1)>' } });
  expect(screen.getByText('<img src=x onerror=alert(1)>')).toBeInTheDocument();
  expect(document.querySelector('.user-caption img')).toBeNull();
  fireEvent.change(screen.getByLabelText('Safe test background'), { target: { value: 'black' } });
  expect(mocks.draw.mock.calls.at(-1)![0]).toEqual(snapshot);
  expect(fetch).not.toHaveBeenCalled(); expect(frames.size).toBe(0);
});
