import * as THREE from 'three';
export type JamCharacter = { root: THREE.Group; animate: (ms: number, airborne: boolean, bank: number) => void; wingMaterial: THREE.MeshPhysicalMaterial };
export function createJamCharacter(own: <T extends THREE.BufferGeometry | THREE.Material>(resource: T) => T): JamCharacter {
  const root = new THREE.Group(); root.name = 'Jam';
  const body = own(new THREE.MeshStandardMaterial({ color: '#252326', roughness: .94 }));
  const highlight = own(new THREE.MeshStandardMaterial({ color: '#51484D', roughness: 1 }));
  const eye = own(new THREE.MeshPhysicalMaterial({ color: '#F14F45', roughness: .29, clearcoat: .28, flatShading: true }));
  const facet = own(new THREE.MeshStandardMaterial({ color: '#6F2430', roughness: .54 }));
  const ivory = own(new THREE.MeshBasicMaterial({ color: '#FFF4DB' }));
  const wingMaterial = own(new THREE.MeshPhysicalMaterial({ color: '#FFF4DB', transparent: true, opacity: .48, roughness: .38,
    metalness: 0, side: THREE.DoubleSide, depthWrite: false }));
  const vein = own(new THREE.LineBasicMaterial({ color: '#baaf96', transparent: true, opacity: .63 }));
  const sphere = own(new THREE.SphereGeometry(1, 24, 16));
  const facets = own(new THREE.IcosahedronGeometry(1, 2));
  const cylinder = own(new THREE.CylinderGeometry(.65, 1, 1, 7));
  function oval(parent: THREE.Object3D, name: string, material: THREE.Material, position: number[], scale: number[], geometry: THREE.BufferGeometry = sphere) {
    const mesh = new THREE.Mesh(geometry, material); mesh.name = name; mesh.position.set(position[0], position[1], position[2]);
    mesh.scale.set(scale[0], scale[1], scale[2]); parent.add(mesh); return mesh;
  }
  function stick(parent: THREE.Object3D, name: string, a: number[], b: number[], radius: number, material = body) {
    const start = new THREE.Vector3(...a as [number, number, number]), end = new THREE.Vector3(...b as [number, number, number]);
    const delta = end.clone().sub(start), mesh = new THREE.Mesh(cylinder, material); mesh.name = name;
    mesh.position.copy(start).add(end).multiplyScalar(.5); mesh.scale.set(radius, delta.length(), radius);
    mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), delta.normalize()); parent.add(mesh); return mesh;
  }
  oval(root, 'rounded thorax', body, [-.07, .04, 0], [.61, .55, .53]);
  const abdomen = oval(root, 'short tapered abdomen', body, [-.84, -.015, 0], [.74, .44, .43]); abdomen.rotation.z = -.055;
  // Three broad transverse ridges read as four segments without a striped bee abdomen.
  for (let segment = 0; segment < 3; segment++) {
    const radius = [.414, .362, .259][segment];
    const ring = new THREE.Mesh(own(new THREE.TorusGeometry(radius, .021, 5, 28)), highlight);
    ring.name = 'abdomen segment'; ring.rotation.y = Math.PI / 2; ring.position.set(-.78 - segment * .24, -.015, 0); root.add(ring);
  }
  oval(root, 'large rounded head', body, [.71, .075, 0], [.6, .59, .58]);
  for (const side of [-1, 1]) {
    const eyeMesh = oval(root, 'compound eye', eye, [.97, .15, side * .395], [.43, .49, .285], facets);
    eyeMesh.rotation.x = side * .12; eyeMesh.rotation.y = side * -.24;
    for (let spot = 0; spot < 4; spot++) {
      oval(root, 'burgundy eye facet', facet, [1.13 - .11 * (spot % 2), -.06 + Math.floor(spot / 2) * .12, side * (.619 + (spot % 2) * .018)], [.044, .053, .011], facets);
    }
    oval(root, 'eye catchlight', ivory, [1.235, .365, side * .527], [.052, .068, .018]);
    oval(root, 'eye catchlight small', ivory, [1.253, .267, side * .56], [.019, .023, .009]);
  }
  oval(root, 'subtle proboscis', highlight, [1.305, -.19, 0], [.14, .066, .065]);
  const antennae: THREE.Group[] = [];
  for (const side of [-1, 1]) {
    const antenna = new THREE.Group(); antenna.name = 'antenna'; antenna.position.set(1.07, .52, side * .17); root.add(antenna); antennae.push(antenna);
    stick(antenna, 'short antenna stem', [0, 0, 0], [.13, .19, side * .025], .022);
    oval(antenna, 'antenna tip', highlight, [.13, .2, side * .025], [.047, .063, .038]);
  }
  const legs: THREE.Group[] = [];
  for (const side of [-1, 1]) for (let index = 0; index < 3; index++) {
    const leg = new THREE.Group(); leg.name = 'leg'; root.add(leg); legs.push(leg);
    const x = .34 - index * .38, spread = (1 - index) * .37;
    const a = [x, -.28, side * .34], b = [x + spread * .65, -.6, side * .69], c = [x + spread, -.98, side * .83];
    stick(leg, 'upper leg', a, b, .044, highlight); oval(leg, 'leg joint', highlight, b, [.049, .049, .049]);
    stick(leg, 'lower leg', b, c, .031, highlight); stick(leg, 'foot', c, [c[0] + .115, c[1] + .025, c[2] + side * .055], .022, highlight);
  }
  const wings: THREE.Group[] = [];
  for (const side of [-1, 1]) {
    const wing = new THREE.Group(); wing.name = 'wing'; wing.position.set(-.12, .4, side * .26); root.add(wing); wings.push(wing);
    const surface = oval(wing, 'ivory wing membrane', wingMaterial, [-.38, .01, side * .94], [.6, .018, 1.13]); surface.rotation.y = side * -.28;
    const edge = own(new THREE.LineBasicMaterial({ color: '#FFF4DB', transparent: true, opacity: .65 }));
    const perimeter: THREE.Vector3[] = [];
    for (let i = 0; i <= 48; i++) {
      const angle = i / 48 * Math.PI * 2;
      const point = new THREE.Vector3(Math.cos(angle) * .6, .025, Math.sin(angle) * 1.13).applyAxisAngle(new THREE.Vector3(0, 1, 0), side * -.28);
      point.add(new THREE.Vector3(-.38, 0, side * .94)); perimeter.push(point);
    }
    wing.add(new THREE.Line(own(new THREE.BufferGeometry().setFromPoints(perimeter)), edge));
    for (const spread of [-.23, .08, .32]) {
      const points = [[0, .028, 0], [-.3 + spread, .028, side * .86], [-.58 + spread, .028, side * 1.8]].map(p => new THREE.Vector3(...p as [number, number, number]));
      wing.add(new THREE.Line(own(new THREE.BufferGeometry().setFromPoints(points)), vein));
    }
  }
  // Sparse, individually readable bristles; shared geometry keeps the mesh budget small.
  for (let i = 0; i < 11; i++) {
    const angle = i * 2.399, x = -.28 + .055 * i, z = Math.sin(angle) * .38, y = .42 + .08 * Math.cos(angle);
    stick(root, 'bristle', [x, y, z], [x - .035, y + .13 + .025 * (i % 3), z * 1.11], .008, highlight);
  }
  return { root, wingMaterial, animate(ms, airborne, bank) {
    // All phase is playback time; repeated timestamps produce exactly repeated decoration.
    wings.forEach((wing, index) => { wing.rotation.x = (index === 0 ? -1 : 1) * (airborne ? .09 + Math.sin(ms * .021) * .045 : .035); });
    antennae.forEach((antenna, index) => { antenna.rotation.z = airborne ? .035 * Math.sin(ms * .002 + index) : 0; });
    legs.forEach((leg, index) => { leg.rotation.x = airborne ? (index < 3 ? -.13 : .13) : 0; });
    root.rotation.x = bank;
  } };
}
