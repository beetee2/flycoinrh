import * as THREE from 'three';
import type { FlightSnapshot } from './contracts';
import schemas from './generated/schemas.json' with { type: 'json' };

// Python contracts own the ground definition, including the historical visual floor.
export const FLIGHT_GROUND = schemas.GroundEnvironment.properties;
export function groundHeight(pose: FlightSnapshot | null): number {
  return pose?.schema_version === 'obs-flight-2' ? pose.environment.ground_z : FLIGHT_GROUND.ground_z.const;
}

export type FlightRenderer = { draw: (pose: FlightSnapshot | null, decorativeMs: number) => void; resize: () => void; dispose: () => void };

export type GraphicsFailureKind = 'context-creation' | 'renderer' | 'context-lost';
export class FlightGraphicsError extends Error {
  constructor(public readonly kind: GraphicsFailureKind, detail: unknown) {
    super(sanitizeGraphicsDetail(detail));
    this.name = 'FlightGraphicsError';
  }
}

/** Keep only a bounded message locally: no stack, URL, profile path, or control characters. */
export function sanitizeGraphicsDetail(detail: unknown): string {
  const message = detail instanceof Error ? detail.message : typeof detail === 'string' ? detail : 'No diagnostic message supplied.';
  return message.replace(/[\u0000-\u001f\u007f-\u009f]/g, ' ')
    .replace(/(?:https?|file|chrome-extension|moz-extension):\/\/[^\s]+/gi, '[URL]')
    .replace(/(?:[A-Za-z]:\\|\/)[^\s,;]+/g, '[path]')
    .replace(/\s+/g, ' ').trim().slice(0, 600) || 'No diagnostic message supplied.';
}

// Match the context requested by the pinned three.js r186, including its alpha:true.
export const FLIGHT_CONTEXT_ATTRIBUTES: WebGLContextAttributes = {
  alpha: true, depth: true, stencil: false, antialias: true, premultipliedAlpha: true,
  preserveDrawingBuffer: false, powerPreference: 'default', failIfMajorPerformanceCaveat: false,
};

/** Original procedural fly. Local three.js geometry only; no imported artwork. */
export function createFlightRenderer(host: HTMLDivElement, onFailure?: (error: FlightGraphicsError) => void): FlightRenderer {
  const canvas = document.createElement('canvas');
  let context: WebGL2RenderingContext | null = null;
  let renderer: THREE.WebGLRenderer | undefined;
  let observer: ResizeObserver | undefined;
  let disposed = false;
  const resources = new Set<THREE.BufferGeometry | THREE.Material>();
  const own = <T extends THREE.BufferGeometry | THREE.Material>(resource: T): T => { resources.add(resource); return resource; };
  function dispose() {
    if (disposed) return;
    disposed = true;
    observer?.disconnect();
    canvas.removeEventListener('webglcontextlost', lost);
    canvas.remove();
    try { resources.forEach(resource => resource.dispose()); }
    finally {
      try { renderer?.dispose(); }
      finally { if (context && !context.isContextLost()) context.getExtension('WEBGL_lose_context')?.loseContext(); }
    }
  }
  function lost(event: Event) {
    event.preventDefault();
    fail(new FlightGraphicsError('context-lost', (event as WebGLContextEvent).statusMessage || 'The browser lost the WebGL2 context.'));
  }
  function fail(error: FlightGraphicsError) {
    if (disposed) return;
    dispose(); onFailure?.(error);
  }
  let creationDetail = '';
  const creationError = (event: Event) => { creationDetail = sanitizeGraphicsDetail((event as WebGLContextEvent).statusMessage); };
  canvas.addEventListener('webglcontextcreationerror', creationError);
  try {
    context = canvas.getContext('webgl2', FLIGHT_CONTEXT_ATTRIBUTES);
    if (!context) throw new Error(creationDetail || 'canvas.getContext("webgl2") returned null; the browser supplied no creation details.');
  } catch (error) {
    dispose(); throw new FlightGraphicsError('context-creation', creationDetail || error);
  } finally { canvas.removeEventListener('webglcontextcreationerror', creationError); }
  try {
  renderer = new THREE.WebGLRenderer({ canvas, context, antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(0xc8ded1);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.domElement.setAttribute('aria-label', '3D fly with six legs and two wings in an open repeating landscape');
  renderer.domElement.setAttribute('role', 'img');
  host.appendChild(renderer.domElement);
  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(0xc8ded1, 32, 110);
  scene.add(new THREE.HemisphereLight(0xfafff0, 0x476b60, 3));
  const sun = new THREE.DirectionalLight(0xfff8db, 4);
  sun.position.set(5, 10, 5);
  scene.add(sun);
  const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 160);
  const fly = new THREE.Group();
  scene.add(fly);
  const body = own(new THREE.MeshStandardMaterial({ color: 0x203b39, metalness: 0.65, roughness: 0.32 }));
  const dark = own(new THREE.MeshStandardMaterial({ color: 0x152320, roughness: 0.5 }));
  const eye = own(new THREE.MeshStandardMaterial({ color: 0xc76c45, metalness: 0.28, roughness: 0.32, flatShading: true }));
  const wingMaterial = own(new THREE.MeshPhysicalMaterial({ color: 0xeafff8, transparent: true, opacity: 0.63,
    roughness: 0.2, metalness: 0.1, side: THREE.DoubleSide, depthWrite: false }));
  const veinMaterial = own(new THREE.LineBasicMaterial({ color: 0x5a8980, transparent: true, opacity: 0.65 }));
  function oval(parent: THREE.Group, material: THREE.Material, position: [number, number, number], scale: [number, number, number], detail = 24) {
    const mesh = new THREE.Mesh(own(new THREE.SphereGeometry(1, detail, 16)), material);
    mesh.position.set(...position); mesh.scale.set(...scale); parent.add(mesh); return mesh;
  }
  oval(fly, body, [0, 0, 0], [0.73, 0.65, 0.62]); // thorax
  oval(fly, body, [-1.05, -0.06, 0], [1.02, 0.51, 0.5]); // abdomen
  oval(fly, dark, [0.85, 0.05, 0], [0.5, 0.5, 0.54]); // head
  for (const side of [-1, 1]) {
    oval(fly, eye, [1.04, 0.14, side * 0.39], [0.33, 0.4, 0.23], 16);
    oval(fly, dark, [1.36, 0.01, side * 0.16], [0.22, 0.065, 0.06]);
    for (let leg = 0; leg < 3; leg++) {
      const x = 0.43 - leg * 0.47;
      const points = [new THREE.Vector3(x, -0.3, side * 0.3), new THREE.Vector3(x + (1 - leg) * 0.3, -0.63, side * 0.99),
        new THREE.Vector3(x + (1 - leg) * 0.61, -1.04, side * 1.15)];
      for (let segment = 0; segment < 2; segment++) {
        const start = points[segment], end = points[segment + 1];
        const direction = end.clone().sub(start);
        const mesh = new THREE.Mesh(own(new THREE.CylinderGeometry(0.035, 0.022, direction.length(), 7)), dark);
        mesh.position.copy(start).add(end).multiplyScalar(0.5);
        mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), direction.normalize());
        fly.add(mesh);
      }
    }
  }
  // Thin ovals and visible veins distinguish the two wings from body geometry.
  const wings: THREE.Group[] = [];
  for (const side of [-1, 1]) {
    const wing = new THREE.Group(); wing.position.set(-0.05, 0.42, side * 0.25); fly.add(wing); wings.push(wing);
    const surface = oval(wing, wingMaterial, [-0.55, 0.02, side * 1.12], [0.74, 0.035, 1.51]);
    surface.rotation.y = side * -0.34;
    for (const spread of [-0.36, 0, 0.36]) {
      const points = [new THREE.Vector3(0, 0.07, 0), new THREE.Vector3(-0.44 + spread, 0.07, side * 1.15), new THREE.Vector3(-0.95 + spread, 0.07, side * 2.27)];
      wing.add(new THREE.Line(own(new THREE.BufferGeometry()).setFromPoints(points), veinMaterial));
    }
  }
  // A repeating grid and deterministic landmarks give parallax without a world boundary.
  const ground = new THREE.Mesh(own(new THREE.PlaneGeometry(260, 260)), own(new THREE.MeshStandardMaterial({ color: 0xb8ccae, roughness: 1 })));
  ground.rotation.x = -Math.PI / 2; ground.position.y = groundHeight(null); scene.add(ground);
  const grid = new THREE.GridHelper(240, 60, 0x799881, 0x9db49b); grid.position.y = groundHeight(null) + 0.02; scene.add(grid);
  own(grid.geometry);
  for (const material of Array.isArray(grid.material) ? grid.material : [grid.material]) own(material);
  const landmarks: THREE.Mesh[] = [];
  const stoneMaterial = own(new THREE.MeshStandardMaterial({ color: 0x799c83, roughness: 0.94, flatShading: true }));
  for (let row = -3; row <= 3; row++) for (let col = -3; col <= 3; col++) {
    const height = 1.5 + ((row + col + 8) % 3) * 1.1;
    const stone = new THREE.Mesh(own(new THREE.ConeGeometry(1.3, height, 5)), stoneMaterial);
    stone.userData = { x: col * 18 + 8, z: row * 18 + 8, height };
    scene.add(stone); landmarks.push(stone);
  }
  let lastPose: FlightSnapshot | null = null;
  let lastTime = 0;
  function draw(pose: FlightSnapshot | null, decorativeMs: number) {
    if (disposed) return;
    lastPose = pose; lastTime = decorativeMs;
    const [x, y, altitude] = pose?.position ?? [0, 0, 0];
    // Rebase only rendered objects around the current pose; authoritative coordinates stay intact.
    fly.position.set(0, 0, 0);
    fly.rotation.set(0, pose?.yaw_rad ?? 0, pose?.pitch_rad ?? 0, 'YXZ');
    wings.forEach((wing, index) => { wing.rotation.x = (index === 0 ? -1 : 1) * (0.13 + Math.sin(decorativeMs * 0.035) * 0.16); });
    const floor = groundHeight(pose) - altitude;
    ground.position.set(0, floor, 0);
    grid.position.set(-(x % 4), floor + 0.02, y % 4);
    for (const stone of landmarks) {
      const wrap = (v: number) => ((v + 63) % 126 + 126) % 126 - 63;
      stone.position.set(wrap(stone.userData.x - x), floor + stone.userData.height / 2, wrap(stone.userData.z + y));
    }
    // Camera follows translation exactly; fixed spectator angle keeps turns legible.
    camera.position.set(-5.9, 4.0, 8.0); camera.lookAt(0, -0.1, 0);
    renderer!.render(scene, camera);
  }
  function resize() {
    if (disposed) return;
    const width = Math.max(host.clientWidth, 1), height = Math.max(host.clientHeight, 1);
    camera.aspect = width / height; camera.updateProjectionMatrix(); renderer!.setSize(width, height); draw(lastPose, lastTime);
  }
  // First draw is part of initialization: a working context alone is not readiness.
  resize();
  observer = new ResizeObserver(() => {
    try { resize(); } catch (error) { fail(new FlightGraphicsError('renderer', error)); }
  });
  observer.observe(host);
  canvas.addEventListener('webglcontextlost', lost);
  return { draw, resize, dispose };
  } catch (error) {
    dispose(); throw new FlightGraphicsError('renderer', error);
  }
}
