import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as THREE from 'three';
import { createFlightRenderer, FlightGraphicsError, FLIGHT_CONTEXT_ATTRIBUTES, FLIGHT_GROUND, sanitizeGraphicsDetail } from '../src/live/flightRenderer';
import type { FlightSnapshot } from '../src/live/contracts';

const mocks = vi.hoisted(() => ({ construct: vi.fn(), render: vi.fn(), setSize: vi.fn(), dispose: vi.fn(), forceContextLoss: vi.fn() }));
vi.mock('three', async importOriginal => ({
  ...await importOriginal<typeof import('three')>(),
  WebGLRenderer: class {
    domElement: HTMLCanvasElement;
    constructor(options: { canvas: HTMLCanvasElement }) { mocks.construct(); this.domElement = options.canvas; }
    setPixelRatio = vi.fn(); setClearColor = vi.fn();
    render = mocks.render; setSize = mocks.setSize; dispose = mocks.dispose; forceContextLoss = mocks.forceContextLoss;
  },
}));

const pose: FlightSnapshot = { schema_version: 'obs-flight-1', session_id: 'synthetic', generation: 1,
  evidence_kind: 'fixture', tick: 2, position: [1000000, 2000000, 3], yaw_rad: 0.5, pitch_rad: 0.1,
  speed_units_s: 2, applied_response_id: null, neutral: false };

const loseContext = vi.fn();
let context: { isContextLost: ReturnType<typeof vi.fn>; getExtension: ReturnType<typeof vi.fn> };
let resize: ResizeObserverCallback;
const disconnect = vi.fn();
beforeEach(() => {
  vi.clearAllMocks(); mocks.construct.mockReset(); mocks.render.mockReset();
  context = { isContextLost: vi.fn(() => false), getExtension: vi.fn(() => ({ loseContext })) };
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation(() => context as unknown as WebGL2RenderingContext);
  vi.stubGlobal('ResizeObserver', class {
    constructor(callback: ResizeObserverCallback) { resize = callback; }
    observe = vi.fn(); disconnect = disconnect;
  });
});

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
    expect(loseContext).toHaveBeenCalledTimes(1); expect(host.querySelectorAll('canvas')).toHaveLength(0);
    expect(disposals.length).toBeGreaterThan(20);
    for (const disposed of disposals) expect(disposed).toHaveBeenCalledTimes(1);
  });
  it('captures creation-event details before Three exists and removes the failed canvas', () => {
    vi.mocked(HTMLCanvasElement.prototype.getContext).mockImplementation(function(this: HTMLCanvasElement) {
      const event = new Event('webglcontextcreationerror');
      Object.defineProperty(event, 'statusMessage', { value: 'BindToCurrentSequence failed' }); this.dispatchEvent(event);
      return null;
    });
    const host = document.createElement('div');
    expect(() => createFlightRenderer(host)).toThrow('BindToCurrentSequence failed');
    expect(mocks.construct).not.toHaveBeenCalled(); expect(host.children).toHaveLength(0);
    expect(HTMLCanvasElement.prototype.getContext).toHaveBeenCalledWith('webgl2', FLIGHT_CONTEXT_ATTRIBUTES);
  });
  it('distinguishes constructor failure and releases its already-created context', () => {
    mocks.construct.mockImplementation(() => { throw new Error('Renderer construction failed'); });
    const host = document.createElement('div');
    try { createFlightRenderer(host); throw new Error('Expected failure'); }
    catch (error) { expect(error).toBeInstanceOf(FlightGraphicsError); expect((error as FlightGraphicsError).kind).toBe('renderer'); }
    expect(loseContext).toHaveBeenCalledTimes(1); expect(host.children).toHaveLength(0);
  });
  it('releases geometry, materials, context, and canvas when the initial scene draw fails', () => {
    const geometry = vi.spyOn(THREE.BufferGeometry.prototype, 'dispose');
    const material = vi.spyOn(THREE.Material.prototype, 'dispose');
    mocks.render.mockImplementationOnce(() => { throw new Error('Scene draw failed'); });
    const host = document.createElement('div');
    expect(() => createFlightRenderer(host)).toThrow('Scene draw failed');
    expect(geometry.mock.calls.length).toBeGreaterThan(20); expect(material.mock.calls.length).toBeGreaterThan(5);
    expect(mocks.dispose).toHaveBeenCalledTimes(1); expect(loseContext).toHaveBeenCalledTimes(1);
    expect(host.children).toHaveLength(0);
    const remount = createFlightRenderer(host); expect(host.children).toHaveLength(1); remount.dispose();
    expect(host.children).toHaveLength(0);
  });
  it('cleans up context loss without restoring or drawing again', () => {
    const host = document.createElement('div'), failure = vi.fn();
    const renderer = createFlightRenderer(host, failure), canvas = host.querySelector('canvas')!;
    const event = new Event('webglcontextlost', { cancelable: true });
    context.isContextLost.mockReturnValue(true); canvas.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(true); expect(failure.mock.calls[0][0].kind).toBe('context-lost');
    expect(disconnect).toHaveBeenCalledTimes(1); expect(mocks.dispose).toHaveBeenCalledTimes(1);
    expect(loseContext).not.toHaveBeenCalled(); expect(host.children).toHaveLength(0);
    const draws = mocks.render.mock.calls.length;
    resize([], {} as ResizeObserver); renderer.draw(pose, 200); renderer.resize(); renderer.dispose();
    canvas.dispatchEvent(new Event('webglcontextrestored'));
    expect(mocks.render).toHaveBeenCalledTimes(draws); expect(failure).toHaveBeenCalledTimes(1);
  });
  it('reports resize failure once and disconnects its observer', () => {
    const failure = vi.fn(), host = document.createElement('div'); createFlightRenderer(host, failure);
    mocks.render.mockImplementation(() => { throw new Error('Resize draw failed'); });
    resize([], {} as ResizeObserver); resize([], {} as ResizeObserver);
    expect(failure).toHaveBeenCalledTimes(1); expect(failure.mock.calls[0][0].kind).toBe('renderer');
    expect(disconnect).toHaveBeenCalledTimes(1); expect(host.children).toHaveLength(0);
  });
  it('bounds diagnostics, excludes paths and URLs, and never retains an error stack', () => {
    const error = new Error('Graphics\n/home/person/profile C:\\Users\\person https://private.test/token');
    expect(sanitizeGraphicsDetail(error)).toBe('Graphics [path] [path] [URL]');
    expect(sanitizeGraphicsDetail('x'.repeat(1000))).toHaveLength(600);
    expect(sanitizeGraphicsDetail({ secret: 'private' })).toBe('No diagnostic message supplied.');
  });

});

describe('ground geometry and camera', () => {
  it('keeps the actual fly geometry above the plane at every decorative extremum and supported pitch', () => {
    const clearance = FLIGHT_GROUND.clearance.const;
    // Continuous support bounds for pitch ±.45; yaw preserves display height.
    const legBound = 1.12 * Math.sin(.45) + 1.04 * Math.cos(.45) + .035;
    const bodyBound = 1.05 * Math.sin(.45) + .06 + Math.hypot(1.02 * Math.sin(.45), .51);
    const wingMinY = .42 + .02 * Math.cos(.29) - 1.12 * Math.sin(.29) - 1.51 * Math.sin(.29) - .035;
    const wingMaxX = .6 + Math.hypot(.74 * Math.cos(.34), 1.51 * Math.sin(.34));
    const wingBound = -wingMinY + wingMaxX * Math.sin(.45);
    const veinBound = -(.42 + .07 * Math.cos(.29) - 2.27 * Math.sin(.29)) + 1.36 * Math.sin(.45);
    expect(Math.max(legBound, bodyBound, wingBound, veinBound)).toBeLessThan(clearance);
    const host = document.createElement('div');
    Object.defineProperty(host, 'clientWidth', { value: 800 }); Object.defineProperty(host, 'clientHeight', { value: 400 });
    const renderer = createFlightRenderer(host);
    let maximumRadius = 0, minimumClearance = Infinity;
    for (const pitch of [-.45, -.225, 0, .225, .45]) for (const yaw of [0, .8, Math.PI, -2]) {
      for (const phase of [-Math.PI / 2, 0, Math.PI / 2, Math.PI]) {
        const contact: FlightSnapshot = { ...pose, schema_version: 'obs-flight-2', physics_id: 'flight-fixed20-ground-v2',
          environment: { environment_id: 'flat-ground-v1', ground_z: FLIGHT_GROUND.ground_z.const as -4,
            collision_proxy: 'fly-clearance-v1', clearance: clearance as 1.5 }, ground_contact: true,
          position: [1234, -5678, FLIGHT_GROUND.ground_z.const + clearance], pitch_rad: pitch, yaw_rad: yaw };
        renderer.draw(contact, phase / .035);
        const [scene, camera] = mocks.render.mock.calls.at(-1)! as [THREE.Scene, THREE.PerspectiveCamera];
        scene.updateMatrixWorld(true); camera.updateMatrixWorld(true);
        const fly = scene.children.find(object => object instanceof THREE.Group)!;
        const floor = scene.children.find(object => object instanceof THREE.Mesh && object.geometry instanceof THREE.PlaneGeometry)!;
        expect(floor.position.y).toBe(-clearance);
        expect(camera.position.y - floor.position.y).toBeGreaterThan(5);
        fly.traverse(object => {
          if (!(object instanceof THREE.Mesh || object instanceof THREE.Line)) return;
          const vertices = object.geometry.getAttribute('position');
          for (let index = 0; index < vertices.count; index++) {
            const vertex = new THREE.Vector3().fromBufferAttribute(vertices, index).applyMatrix4(object.matrixWorld);
            maximumRadius = Math.max(maximumRadius, vertex.length());
            minimumClearance = Math.min(minimumClearance, vertex.y - floor.position.y);
          }
        });
      }
    }
    expect(maximumRadius).toBeLessThan(3.2);
    expect(minimumClearance).toBeGreaterThan(0);
    renderer.dispose();
  });
  it('faithfully retains a historical below-ground path without a display clamp', () => {
    const renderer = createFlightRenderer(document.createElement('div'));
    const below = { ...pose, position: [0, 0, -8.14] as [number, number, number] };
    renderer.draw(below, 0);
    const scene = mocks.render.mock.calls.at(-1)![0] as THREE.Scene;
    const floor = scene.children.find(object => object instanceof THREE.Mesh && object.geometry instanceof THREE.PlaneGeometry)!;
    expect(floor.position.y).toBeCloseTo(4.14);
    expect(below.position[2]).toBe(-8.14);
    renderer.dispose();
  });
});
