import { describe, expect, it, vi } from 'vitest';
import * as THREE from 'three';
import { createFlightRenderer } from '../src/live/flightRenderer';
import type { FlightSnapshot } from '../src/live/contracts';

const mocks = vi.hoisted(() => ({ render: vi.fn(), setSize: vi.fn(), dispose: vi.fn(), forceContextLoss: vi.fn() }));
vi.mock('three', async importOriginal => ({
  ...await importOriginal<typeof import('three')>(),
  WebGLRenderer: class {
    domElement = document.createElement('canvas');
    setPixelRatio = vi.fn(); setClearColor = vi.fn();
    render = mocks.render; setSize = mocks.setSize; dispose = mocks.dispose; forceContextLoss = mocks.forceContextLoss;
  },
}));

const pose: FlightSnapshot = { schema_version: 'obs-flight-1', session_id: 'synthetic', generation: 1,
  evidence_kind: 'fixture', tick: 2, position: [1000000, 2000000, 3], yaw_rad: 0.5, pitch_rad: 0.1,
  speed_units_s: 2, applied_response_id: null, neutral: false };

describe('procedural renderer ownership', () => {
  it('rebases only presentation, resizes once per notification, and disposes all GPU resources once', () => {
    let resize: ResizeObserverCallback;
    const disconnect = vi.fn();
    vi.stubGlobal('ResizeObserver', class {
      constructor(callback: ResizeObserverCallback) { resize = callback; }
      observe = vi.fn(); disconnect = disconnect;
    });
    mocks.render.mockClear(); mocks.setSize.mockClear(); mocks.dispose.mockClear(); mocks.forceContextLoss.mockClear();
    const host = document.createElement('div');
    Object.defineProperty(host, 'clientWidth', { value: 800 }); Object.defineProperty(host, 'clientHeight', { value: 400 });
    const renderer = createFlightRenderer(host);
    expect(host.querySelectorAll('canvas')).toHaveLength(1);
    expect(mocks.setSize).toHaveBeenCalledWith(800, 400);
    const before = structuredClone(pose);
    renderer.draw(pose, 200);
    expect(pose).toEqual(before);
    const scene = mocks.render.mock.calls.at(-1)![0] as THREE.Scene;
    const fly = scene.children.find(object => object instanceof THREE.Group)!;
    expect(fly.position.toArray()).toEqual([0, 0, 0]);
    expect(fly.rotation.y).toBe(0.5); expect(fly.rotation.z).toBe(0.1);
    const disposals: ReturnType<typeof vi.fn>[] = [];
    const resources = new Set<THREE.BufferGeometry | THREE.Material>();
    scene.traverse(object => {
      if (object instanceof THREE.Mesh || object instanceof THREE.Line) {
        resources.add(object.geometry);
        for (const material of Array.isArray(object.material) ? object.material : [object.material]) resources.add(material);
      }
    });
    for (const resource of resources) { const disposed = vi.fn(); resource.addEventListener('dispose', disposed); disposals.push(disposed); }
    const frames = mocks.render.mock.calls.length;
    resize!([], {} as ResizeObserver);
    expect(mocks.render).toHaveBeenCalledTimes(frames + 1);
    renderer.dispose(); renderer.dispose();
    expect(disconnect).toHaveBeenCalledTimes(1); expect(mocks.dispose).toHaveBeenCalledTimes(1);
    expect(mocks.forceContextLoss).toHaveBeenCalledTimes(1); expect(host.querySelectorAll('canvas')).toHaveLength(0);
    expect(disposals.length).toBeGreaterThan(20);
    for (const disposed of disposals) expect(disposed).toHaveBeenCalledTimes(1);
  });
});
