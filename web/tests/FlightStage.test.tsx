import { StrictMode } from 'react';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { FlightStage } from '../src/live/FlightStage';

const mocks = vi.hoisted(() => ({ create: vi.fn(), draw: vi.fn(), dispose: vi.fn() }));
vi.mock('../src/live/flightRenderer', () => ({ createFlightRenderer: mocks.create }));
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
  mocks.draw.mockClear(); mocks.dispose.mockClear();
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
    render(<FlightStage />); expect(screen.getByRole('status')).toHaveTextContent('3D view unavailable');
    await load(); expect(screen.getByRole('button', { name: 'Play synthetic preview' })).toBeDisabled(); expect(frames.size).toBe(0);
  });
  it('freezes immediately if the WebGL context is lost', async () => {
    render(<FlightStage />); await load(); fireEvent.click(screen.getByRole('button', { name: 'Play synthetic preview' })); advance(100);
    fireEvent(screen.getByTestId('flight-canvas'), new Event('webglcontextlost'));
    expect(frames.size).toBe(0); expect(screen.getByRole('button', { name: 'Play synthetic preview' })).toBeDisabled();
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
