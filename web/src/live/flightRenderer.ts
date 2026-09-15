import * as THREE from 'three';
import type { FlightSnapshot } from './contracts';

export type FlightRenderer = { draw: (pose: FlightSnapshot | null, decorativeMs: number) => void; resize: () => void; dispose: () => void };

/** Original procedural fly. Local three.js geometry only; no imported artwork. */
export function createFlightRenderer(host: HTMLDivElement): FlightRenderer {
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
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
  const body = new THREE.MeshStandardMaterial({ color: 0x203b39, metalness: 0.65, roughness: 0.32 });
  const dark = new THREE.MeshStandardMaterial({ color: 0x152320, roughness: 0.5 });
  const eye = new THREE.MeshStandardMaterial({ color: 0xc76c45, metalness: 0.28, roughness: 0.32, flatShading: true });
  const wingMaterial = new THREE.MeshPhysicalMaterial({ color: 0xeafff8, transparent: true, opacity: 0.63,
    roughness: 0.2, metalness: 0.1, side: THREE.DoubleSide, depthWrite: false });
  const veinMaterial = new THREE.LineBasicMaterial({ color: 0x5a8980, transparent: true, opacity: 0.65 });
  function oval(parent: THREE.Group, material: THREE.Material, position: [number, number, number], scale: [number, number, number], detail = 24) {
    const mesh = new THREE.Mesh(new THREE.SphereGeometry(1, detail, 16), material);
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
        const mesh = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.022, direction.length(), 7), dark);
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
      wing.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(points), veinMaterial));
    }
  }
  // A repeating grid and deterministic landmarks give parallax without a world boundary.
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(260, 260), new THREE.MeshStandardMaterial({ color: 0xb8ccae, roughness: 1 }));
  ground.rotation.x = -Math.PI / 2; ground.position.y = -4; scene.add(ground);
  const grid = new THREE.GridHelper(240, 60, 0x799881, 0x9db49b); grid.position.y = -3.98; scene.add(grid);
  const landmarks: THREE.Mesh[] = [];
  const stoneMaterial = new THREE.MeshStandardMaterial({ color: 0x799c83, roughness: 0.94, flatShading: true });
  for (let row = -3; row <= 3; row++) for (let col = -3; col <= 3; col++) {
    const height = 1.5 + ((row + col + 8) % 3) * 1.1;
    const stone = new THREE.Mesh(new THREE.ConeGeometry(1.3, height, 5), stoneMaterial);
    stone.userData = { x: col * 18 + 8, z: row * 18 + 8, height };
    scene.add(stone); landmarks.push(stone);
  }
  let lastPose: FlightSnapshot | null = null;
  let lastTime = 0;
  function draw(pose: FlightSnapshot | null, decorativeMs: number) {
    lastPose = pose; lastTime = decorativeMs;
    const [x, y, altitude] = pose?.position ?? [0, 0, 0];
    // Rebase only rendered objects around the current pose; authoritative coordinates stay intact.
    fly.position.set(0, 0, 0);
    fly.rotation.set(0, pose?.yaw_rad ?? 0, pose?.pitch_rad ?? 0, 'YXZ');
    wings.forEach((wing, index) => { wing.rotation.x = (index === 0 ? -1 : 1) * (0.13 + Math.sin(decorativeMs * 0.035) * 0.16); });
    ground.position.set(0, -4 - altitude, 0);
    grid.position.set(-(x % 4), -3.98 - altitude, y % 4);
    for (const stone of landmarks) {
      const wrap = (v: number) => ((v + 63) % 126 + 126) % 126 - 63;
      stone.position.set(wrap(stone.userData.x - x), -4 - altitude + stone.userData.height / 2, wrap(stone.userData.z + y));
    }
    // Camera follows translation exactly; fixed spectator angle keeps turns legible.
    camera.position.set(-5.9, 4.0, 8.0); camera.lookAt(0, -0.1, 0);
    renderer.render(scene, camera);
  }
  function resize() {
    const width = Math.max(host.clientWidth, 1), height = Math.max(host.clientHeight, 1);
    camera.aspect = width / height; camera.updateProjectionMatrix(); renderer.setSize(width, height); draw(lastPose, lastTime);
  }
  const observer = new ResizeObserver(resize); observer.observe(host); resize();
  let disposed = false;
  return { draw, resize, dispose() {
    if (disposed) return; disposed = true; observer.disconnect();
    const geometries = new Set<THREE.BufferGeometry>(), materials = new Set<THREE.Material>();
    scene.traverse(object => {
      if (object instanceof THREE.Mesh || object instanceof THREE.Line) {
        geometries.add(object.geometry);
        for (const material of Array.isArray(object.material) ? object.material : [object.material]) materials.add(material);
      }
    });
    geometries.forEach(geometry => geometry.dispose()); materials.forEach(material => material.dispose());
    renderer.dispose(); renderer.forceContextLoss(); renderer.domElement.remove();
  } };
}
