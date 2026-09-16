import * as THREE from 'three';
import type { FlightSnapshot } from './contracts';
import { createJamCharacter } from './jamCharacter';
import { DEFAULT_PRESENTATION_SETTINGS, parsePresentationSettings, type PresentationSettings } from './presentationSettings';
import { FlightGraphicsError, FLIGHT_CONTEXT_ATTRIBUTES, groundHeight, sanitizeGraphicsDetail, type FlightRenderer } from './flightRenderer';

/** Declared rigid world-to-render transform, followed only by a uniform origin subtraction. */
export function worldToRender(position: readonly number[]): THREE.Vector3 { return new THREE.Vector3(position[0], position[2], -position[1]); }
export function createScreenGremlinRenderer(host: HTMLDivElement, onFailure?: (error: FlightGraphicsError) => void,
  initialSettings: PresentationSettings = { ...DEFAULT_PRESENTATION_SETTINGS }): FlightRenderer {
  let settings = parsePresentationSettings(initialSettings);
  const canvas = document.createElement('canvas');
  let context: WebGL2RenderingContext | null = null, renderer: THREE.WebGLRenderer | undefined, observer: ResizeObserver | undefined;
  let disposed = false;
  const resources = new Set<THREE.BufferGeometry | THREE.Material>();
  const own = <T extends THREE.BufferGeometry | THREE.Material>(resource: T): T => { resources.add(resource); return resource; };
  function dispose() {
    if (disposed) return; disposed = true;
    observer?.disconnect(); canvas.removeEventListener('webglcontextlost', lost); canvas.remove();
    try { resources.forEach(resource => resource.dispose()); } finally {
      try { renderer?.dispose(); } finally { if (context && !context.isContextLost()) context.getExtension('WEBGL_lose_context')?.loseContext(); }
    }
  }
  function fail(error: FlightGraphicsError) { if (!disposed) { dispose(); onFailure?.(error); } }
  function lost(event: Event) { event.preventDefault(); fail(new FlightGraphicsError('context-lost', (event as WebGLContextEvent).statusMessage || 'The browser lost the WebGL2 context.')); }
  let detail = '';
  const creationError = (event: Event) => { detail = sanitizeGraphicsDetail((event as WebGLContextEvent).statusMessage); };
  canvas.addEventListener('webglcontextcreationerror', creationError);
  try {
    context = canvas.getContext('webgl2', FLIGHT_CONTEXT_ATTRIBUTES);
    if (!context) throw new Error(detail || 'canvas.getContext("webgl2") returned null; the browser supplied no creation details.');
  } catch (error) { dispose(); throw new FlightGraphicsError('context-creation', detail || error); }
  finally { canvas.removeEventListener('webglcontextcreationerror', creationError); }
  try {
    renderer = new THREE.WebGLRenderer({ canvas, context, antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2)); renderer.setClearColor(0, 0); renderer.outputColorSpace = THREE.SRGBColorSpace;
    canvas.setAttribute('aria-label', 'Jam, a handmade charcoal fly with cherry-red eyes, six legs and two ivory wings in front of your screen'); canvas.setAttribute('role', 'img');
    host.appendChild(canvas);
    const scene = new THREE.Scene();
    scene.add(new THREE.HemisphereLight(0xfff4db, 0x7a8091, 2.2));
    const key = new THREE.DirectionalLight(0xffefd3, settings.keyLightIntensity); key.position.set(4, 9, 6); scene.add(key);
    const rim = new THREE.DirectionalLight(0xfff9ec, 2); rim.position.set(-5, 3, -5); scene.add(rim);
    const camera = new THREE.PerspectiveCamera(settings.cameraFov, 1, .1, 160);
    const jam = createJamCharacter(own); scene.add(jam.root);
    // A softly fading pool of light on the actual floor; no polygon edge or horizon.
    const groundMaterial = own(new THREE.ShaderMaterial({ transparent: true, depthWrite: false, side: THREE.DoubleSide,
      uniforms: { opacity: { value: .14 } },
      vertexShader: 'varying vec2 vUv; void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',
      fragmentShader: 'varying vec2 vUv;uniform float opacity;void main(){float d=length((vUv-.5)*2.);gl_FragColor=vec4(.91,.89,.85,opacity*(1.-smoothstep(.0,1.,d)));}',
    }));
    const ground = new THREE.Mesh(own(new THREE.PlaneGeometry(12, 9)), groundMaterial);
    ground.name = 'authoritative ground'; ground.rotation.x = -Math.PI / 2; scene.add(ground);
    const shadowMaterial = own(new THREE.ShaderMaterial({ transparent: true, depthWrite: false,
      uniforms: { opacity: { value: .2 } },
      vertexShader: 'varying vec2 vUv; void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',
      fragmentShader: 'varying vec2 vUv;uniform float opacity;void main(){float d=length((vUv-.5)*2.);gl_FragColor=vec4(.12,.10,.13,opacity*(1.-smoothstep(.05,1.,d)));}',
    }));
    const shadow = new THREE.Mesh(own(new THREE.PlaneGeometry(3.6, 2.8)), shadowMaterial); shadow.name = 'ground contact shadow'; shadow.rotation.x = -Math.PI / 2; scene.add(shadow);
    const origin = new THREE.Vector3(), follow = new THREE.Vector3();
    let initialized = false, lastPose: FlightSnapshot | null = null, lastTime = 0, anchorYaw = 0, anchorTime = 0;
    function resetHistory() { initialized = false; }
    function draw(pose: FlightSnapshot | null, decorativeMs: number) {
      if (disposed) return;
      const world = worldToRender(pose?.position ?? [0, 0, 0]);
      const newIdentity = pose?.session_id !== lastPose?.session_id || pose?.generation !== lastPose?.generation;
      if (!initialized || newIdentity || decorativeMs < lastTime) {
        origin.copy(world); follow.set(0, 0, 0); initialized = true; anchorYaw = pose?.yaw_rad ?? 0; anchorTime = decorativeMs; lastTime = decorativeMs;
      }
      const local = world.sub(origin);
      const airborne = Boolean(pose && !pose.neutral && !(pose.schema_version === 'obs-flight-2' && pose.ground_contact));
      // Analytic soft dead zone: schedule independent and stationary whenever the pose is.
      // Its continuous derivative gives a gentle transition without a trailing camera integrator.
      // Reserve wing space in narrow compositions. These bounds control only the
      // camera's dead zone; Jam retains its entire authoritative displacement.
      const tangent = Math.tan(THREE.MathUtils.degToRad(settings.cameraFov / 2));
      const distance = Math.max(settings.cameraDistance, 2.85 / (tangent * Math.min(camera.aspect, 1)));
      const viewDirection = new THREE.Vector3(.56, .31, .77).normalize();
      const right = new THREE.Vector3(.77, 0, -.56).normalize();
      const up = new THREE.Vector3().crossVectors(viewDirection, right).normalize();
      const horizontalBudget = Math.max(.08, distance * tangent * camera.aspect - 2.7);
      const verticalBudget = Math.max(.08, distance * tangent - 2.6);
      const depthBudget = Math.min(1, horizontalBudget);
      follow.set(0, 0, 0);
      for (const [axis, budget] of [[right, horizontalBudget], [up, verticalBudget], [viewDirection, depthBudget]] as const) {
        const coordinate = local.dot(axis), deadZone = Math.min(settings.followDeadZone, budget * .58);
        const softness = Math.min(1.25, budget * .42), excess = Math.max(0, Math.abs(coordinate) - deadZone);
        follow.addScaledVector(axis, Math.sign(coordinate) * excess * excess / (excess + softness));
      }
      const elapsed = (decorativeMs - anchorTime) / 1000;
      const headingChange = Math.atan2(Math.sin((pose?.yaw_rad ?? 0) - anchorYaw), Math.cos((pose?.yaw_rad ?? 0) - anchorYaw));
      // Small mean-turn bank uses only authoritative headings and clip time, never render FPS.
      const bank = airborne && elapsed > 0 ? THREE.MathUtils.clamp(-headingChange / elapsed * .035, -.045, .045) : 0;
      jam.root.position.copy(local); jam.root.rotation.set(0, pose?.yaw_rad ?? 0, pose?.pitch_rad ?? 0, 'YXZ');
      jam.animate(decorativeMs, airborne, bank); jam.wingMaterial.opacity = settings.wingOpacity;
      const floor = groundHeight(pose) - origin.y;
      ground.position.set(local.x, floor, local.z);
      shadow.position.set(local.x, floor + .009, local.z);
      const height = (pose?.position[2] ?? 0) - groundHeight(pose);
      shadow.visible = height >= 0;
      groundMaterial.uniforms.opacity.value = .18 * Math.exp(-Math.max(0, height - 1.5) * .8);
      shadowMaterial.uniforms.opacity.value = .28 * Math.exp(-Math.max(0, height - 1.5) * .65);
      shadow.scale.setScalar(1 + Math.max(0, height - 1.5) * .13);
      // Fixed three-quarter spectator azimuth; camera height guard never moves the fly or floor.
      camera.position.copy(follow).add(viewDirection.multiplyScalar(distance));
      if (pose?.schema_version === 'obs-flight-2' || !pose) camera.position.y = Math.max(camera.position.y, floor + .5);
      camera.lookAt(follow.x, follow.y -.05, follow.z);
      key.intensity = settings.keyLightIntensity;
      lastPose = pose; lastTime = decorativeMs;
      renderer!.render(scene, camera);
    }
    function resize() {
      if (disposed) return;
      const width = Math.max(host.clientWidth, 1), height = Math.max(host.clientHeight, 1);
      camera.aspect = width / height; camera.updateProjectionMatrix(); renderer!.setSize(width, height); draw(lastPose, lastTime);
    }
    function updateSettings(next: PresentationSettings) {
      settings = parsePresentationSettings(next); camera.fov = settings.cameraFov; camera.updateProjectionMatrix(); draw(lastPose, lastTime);
    }
    resize(); observer = new ResizeObserver(() => { try { resize(); } catch (error) { fail(new FlightGraphicsError('renderer', error)); } }); observer.observe(host);
    canvas.addEventListener('webglcontextlost', lost);
    return { draw, resize, dispose, resetHistory, updateSettings };
  } catch (error) { dispose(); throw new FlightGraphicsError('renderer', error); }
}
