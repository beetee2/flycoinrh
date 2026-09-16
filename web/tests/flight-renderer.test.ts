import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as THREE from 'three';
import { createLegacyFlightRenderer as createFlightRenderer, createFlightRenderer as createGremlinRenderer, FlightGraphicsError, FLIGHT_CONTEXT_ATTRIBUTES, FLIGHT_GROUND, sanitizeGraphicsDetail } from '../src/live/flightRenderer';
import { createJamCharacter } from '../src/live/jamCharacter';
import { DEFAULT_PRESENTATION_SETTINGS } from '../src/live/presentationSettings';
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


describe('Screen Gremlin presentation boundary', () => {
  it('keeps six legs, two wings, and a shared modest material budget with no scenery or fog', () => {
    const renderer = createGremlinRenderer(document.createElement('div'));
    const scene = mocks.render.mock.calls.at(-1)![0] as THREE.Scene;
    const fly = scene.getObjectByName('Jam')!;
    expect(fly.children.filter(child => child.name === 'leg')).toHaveLength(6);
    expect(fly.children.filter(child => child.name === 'wing')).toHaveLength(2);
    expect(scene.fog).toBeNull();
    expect(scene.children.some(child => child instanceof THREE.GridHelper)).toBe(false);
    const materials = new Set<THREE.Material>();
    fly.traverse(object => { if (object instanceof THREE.Mesh || object instanceof THREE.Line) for (const material of Array.isArray(object.material) ? object.material : [object.material]) materials.add(material); });
    expect(materials.size).toBeLessThanOrEqual(10);
    renderer.dispose();
  });
  it('preserves actual world displacement inside a camera dead zone and freezes on repeated playback time', () => {
    const renderer = createGremlinRenderer(document.createElement('div'));
    const first = structuredClone(pose);
    renderer.draw(first, 0);
    const [scene, camera] = mocks.render.mock.calls.at(-1)! as [THREE.Scene, THREE.PerspectiveCamera];
    const cameraBefore = camera.position.clone();
    const next: FlightSnapshot = { ...first, position: [first.position[0] + .4, first.position[1] + .2, first.position[2] + .1], tick: 3 };
    const copy = structuredClone(next);
    renderer.draw(next, 20);
    const fly = scene.getObjectByName('Jam')!;
    expect(fly.position.x).toBeCloseTo(.4); expect(fly.position.y).toBeCloseTo(.1); expect(fly.position.z).toBeCloseTo(-.2);
    expect(camera.position.toArray()).toEqual(cameraBefore.toArray());
    const transform = fly.matrix.clone();
    for (let i = 0; i < 10; i++) renderer.draw(next, 20);
    expect(camera.position.toArray()).toEqual(cameraBefore.toArray());
    expect(fly.matrix).toEqual(transform); expect(next).toEqual(copy); expect(first).toEqual(pose);
    renderer.dispose();
  });
  it('resets camera and secondary animation repeatably; view settings do not mutate trajectory', () => {
    const renderer = createGremlinRenderer(document.createElement('div'));
    const sequence = Array.from({ length: 10 }, (_, index) => ({ ...pose, tick: index, position: [index * .6, index * -.1, 0] as [number, number, number], yaw_rad: index * .02 }));
    function play() {
      renderer.resetHistory?.();
      return sequence.map((snapshot, index) => {
        renderer.draw(snapshot, index * 20);
        const [scene, camera] = mocks.render.mock.calls.at(-1)! as [THREE.Scene, THREE.PerspectiveCamera];
        return { position: scene.getObjectByName('Jam')!.position.toArray(), rotation: scene.getObjectByName('Jam')!.rotation.toArray(), camera: camera.position.toArray() };
      });
    }
    expect(play()).toEqual(play());
    const original = structuredClone(sequence);
    renderer.updateSettings?.({ ...DEFAULT_PRESENTATION_SETTINGS, caption: '<b>hello</b>', cameraDistance: 22, wingOpacity: .2 });
    play(); expect(sequence).toEqual(original);
    renderer.dispose();
  });
  it('produces the same camera and character transforms under different render schedules', () => {
    const renderer = createGremlinRenderer(document.createElement('div'));
    function renderSchedule(times: number[]) {
      renderer.resetHistory?.();
      for (const ms of times) renderer.draw({ ...pose, tick: ms / 20, position: [ms * .006, ms * .002, -ms * .001], yaw_rad: ms * .0004 }, ms);
      const [scene, camera] = mocks.render.mock.calls.at(-1)! as [THREE.Scene, THREE.PerspectiveCamera];
      scene.updateMatrixWorld(true); camera.updateMatrixWorld(true);
      const transforms: number[][] = [];
      scene.getObjectByName('Jam')!.traverse(object => transforms.push(object.matrixWorld.toArray()));
      return { camera: camera.matrixWorld.toArray(), transforms };
    }
    const dense = Array.from({ length: 121 }, (_, i) => i * 1000 / 120);
    expect(renderSchedule([0, 200, 400, 600, 800, 1000])).toEqual(renderSchedule(dense));
    expect(renderSchedule([0, 1000])).toEqual(renderSchedule(dense));
    renderer.dispose();
  });
  it('keeps actual mesh vertices above v2 ground through contact, ascent, turn, and descent poses', () => {
    const renderer = createGremlinRenderer(document.createElement('div'));
    let minimum = Infinity;
    for (const contact of [true, false]) for (const pitch of [-.45, -.225, 0, .225, .45]) for (const yaw of [-Math.PI, -.8, 0, 1, Math.PI]) for (const ms of [0, 25, 75, 150, 225]) {
      const snapshot: FlightSnapshot = { ...pose, schema_version: 'obs-flight-2', physics_id: 'flight-fixed20-ground-v2', environment: { environment_id: 'flat-ground-v1', ground_z: -4, collision_proxy: 'fly-clearance-v1', clearance: 1.5 }, ground_contact: contact, pitch_rad: pitch, yaw_rad: yaw, position: [20, 30, -2.5] };
      renderer.draw(snapshot, ms);
      const [scene, camera] = mocks.render.mock.calls.at(-1)! as [THREE.Scene, THREE.PerspectiveCamera]; scene.updateMatrixWorld(true);
      const floor = scene.getObjectByName('authoritative ground')!;
      expect(camera.position.y).toBeGreaterThan(floor.position.y + .49);
      scene.getObjectByName('Jam')!.traverse(object => {
        if (!(object instanceof THREE.Mesh || object instanceof THREE.Line)) return;
        const vertices = object.geometry.getAttribute('position');
        for (let index = 0; index < vertices.count; index++) {
          const vertex = new THREE.Vector3().fromBufferAttribute(vertices, index).applyMatrix4(object.matrixWorld);
          minimum = Math.min(minimum, vertex.y - floor.position.y);
        }
      });
    }
    expect(minimum).toBeGreaterThan(.05); renderer.dispose();
  });
  it('covers maximum decorative bank and flight-leg tuck within the unchanged clearance', () => {
    const resources = new Set<THREE.BufferGeometry | THREE.Material>();
    const jam = createJamCharacter(resource => { resources.add(resource); return resource; });
    let maximumDownwardSupport = 0;
    for (const pitch of [-.45, 0, .45]) for (const bank of [-.045, 0, .045]) for (const time of [0, Math.PI / 2 / .021, Math.PI * 1.5 / .021]) {
      jam.root.rotation.set(0, 0, pitch, 'YXZ'); jam.animate(time, true, bank); jam.root.updateMatrixWorld(true);
      jam.root.traverse(object => {
        if (!(object instanceof THREE.Mesh || object instanceof THREE.Line)) return;
        const vertices = object.geometry.getAttribute('position');
        for (let i = 0; i < vertices.count; i++) maximumDownwardSupport = Math.max(maximumDownwardSupport, -new THREE.Vector3().fromBufferAttribute(vertices, i).applyMatrix4(object.matrixWorld).y);
      });
    }
    expect(maximumDownwardSupport).toBeLessThan(1.45);
    resources.forEach(resource => resource.dispose());
  });
  it('keeps actual character geometry inside the portrait frustum across moving turns', () => {
    const host = document.createElement('div');
    Object.defineProperty(host, 'clientWidth', { value: 450 }); Object.defineProperty(host, 'clientHeight', { value: 800 });
    const renderer = createGremlinRenderer(host);
    renderer.draw({ ...pose, position: [0, 0, 0], yaw_rad: 0 }, 0);
    let maximum = 0;
    for (let step = 1; step <= 30; step++) {
      const snapshot: FlightSnapshot = { ...pose, schema_version: 'obs-flight-2', physics_id: 'flight-fixed20-ground-v2', environment: { environment_id: 'flat-ground-v1', ground_z: -4, collision_proxy: 'fly-clearance-v1', clearance: 1.5 }, ground_contact: step % 2 === 0, position: [step * 1.2, step * -.8, -2.5], yaw_rad: step * Math.PI / 15, pitch_rad: Math.sin(step) * .45 };
      const before = structuredClone(snapshot);
      renderer.draw(snapshot, step * 200);
      const [scene, camera] = mocks.render.mock.calls.at(-1)! as [THREE.Scene, THREE.PerspectiveCamera];
      scene.updateMatrixWorld(true); camera.updateMatrixWorld(true);
      scene.getObjectByName('Jam')!.traverse(object => {
        if (!(object instanceof THREE.Mesh || object instanceof THREE.Line)) return;
        const vertices = object.geometry.getAttribute('position');
        for (let i = 0; i < vertices.count; i++) {
          const projected = new THREE.Vector3().fromBufferAttribute(vertices, i).applyMatrix4(object.matrixWorld).project(camera);
          maximum = Math.max(maximum, Math.abs(projected.x), Math.abs(projected.y));
        }
      });
      expect(snapshot).toEqual(before);
      expect(scene.getObjectByName('Jam')!.position.toArray()).toEqual([step * 1.2, -2.5, step * .8]);
    }
    expect(maximum).toBeLessThan(.96); renderer.dispose();
  });
  it('preserves historical v1 below-ground semantics in Screen Gremlin', () => {
    const renderer = createGremlinRenderer(document.createElement('div'));
    renderer.draw({ ...pose, position: [0, 0, -8.14] }, 0);
    const scene = mocks.render.mock.calls.at(-1)![0] as THREE.Scene;
    expect(scene.getObjectByName('authoritative ground')!.position.y).toBeCloseTo(4.14);
    expect(scene.getObjectByName('Jam')!.position.y).toBe(0);
    renderer.dispose();
  });
  it('stops after context loss and allows a fresh explicit renderer recreation', () => {
    const host = document.createElement('div'), failure = vi.fn();
    const renderer = createGremlinRenderer(host, failure), canvas = host.querySelector('canvas')!;
    context.isContextLost.mockReturnValue(true);
    canvas.dispatchEvent(new Event('webglcontextlost', { cancelable: true }));
    const calls = mocks.render.mock.calls.length;
    renderer.draw(pose, 500); renderer.resize(); resize([], {} as ResizeObserver);
    expect(mocks.render).toHaveBeenCalledTimes(calls); expect(failure).toHaveBeenCalledTimes(1);
    expect(failure.mock.calls[0][0].kind).toBe('context-lost'); expect(host.children).toHaveLength(0);
    context.isContextLost.mockReturnValue(false);
    const retry = createGremlinRenderer(host); expect(host.querySelectorAll('canvas')).toHaveLength(1); retry.dispose();
  });
  it('disposes candidate resources when its first render fails', () => {
    const geometry = vi.spyOn(THREE.BufferGeometry.prototype, 'dispose'), material = vi.spyOn(THREE.Material.prototype, 'dispose');
    mocks.render.mockImplementationOnce(() => { throw new Error('Candidate initial draw failed'); });
    const host = document.createElement('div');
    expect(() => createGremlinRenderer(host)).toThrow('Candidate initial draw failed');
    expect(geometry).toHaveBeenCalled(); expect(material).toHaveBeenCalled();
    expect(loseContext).toHaveBeenCalledTimes(1); expect(host.children).toHaveLength(0);
  });
  it('reuses and releases every scene geometry/material, context, and canvas exactly once', () => {
    const host = document.createElement('div'); const renderer = createGremlinRenderer(host);
    const scene = mocks.render.mock.calls.at(-1)![0] as THREE.Scene;
    const resources = new Set<THREE.BufferGeometry | THREE.Material>();
    scene.traverse(object => { if (object instanceof THREE.Mesh || object instanceof THREE.Line) { resources.add(object.geometry); for (const material of Array.isArray(object.material) ? object.material : [object.material]) resources.add(material); } });
    const released = [...resources].map(resource => { const callback = vi.fn(); resource.addEventListener('dispose', callback); return callback; });
    const geometry = vi.spyOn(THREE.BufferGeometry.prototype, 'clone');
    for (let ms = 0; ms < 1000; ms += 20) renderer.draw(pose, ms);
    expect(geometry).not.toHaveBeenCalled();
    renderer.dispose(); renderer.dispose();
    for (const callback of released) expect(callback).toHaveBeenCalledTimes(1);
    expect(host.children).toHaveLength(0); expect(disconnect).toHaveBeenCalledTimes(1); expect(loseContext).toHaveBeenCalledTimes(1);
  });
});
