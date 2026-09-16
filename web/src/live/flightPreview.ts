import { parseLiveContract, type FlightSnapshot } from './contracts';

export type FlightPreview = { schema_version: 'obs-flight-preview-1'; evidence_kind: 'synthetic'; dt_ms: 20; snapshots: FlightSnapshot[] };

/** A bounded, labeled presentation sequence. Every pose comes from server physics. */
export function parseFlightPreview(value: unknown): FlightPreview {
  return parseLiveContract('SyntheticFlightPreview', value);
}

/** Display interpolation only: never advances, invents, or feeds back physics. */
export function previewPose(preview: FlightPreview, elapsedMs: number): FlightSnapshot {
  const fractionalTick = Math.max(0, Math.min(elapsedMs / preview.dt_ms, preview.snapshots.length - 1));
  const index = Math.floor(fractionalTick);
  const a = preview.snapshots[index];
  const b = preview.snapshots[Math.min(index + 1, preview.snapshots.length - 1)];
  const blend = fractionalTick - index;
  return interpolatePose(a, b, blend);
}

/** Bounded interpolation of legitimate poses, never extrapolation. */
export function interpolatePose(a: FlightSnapshot, b: FlightSnapshot, amount: number): FlightSnapshot {
  if (a.session_id !== b.session_id || a.generation !== b.generation || b.tick < a.tick ||
      a.schema_version !== b.schema_version || (a.schema_version === 'obs-flight-2' &&
      (b.schema_version !== 'obs-flight-2' || a.physics_id !== b.physics_id ||
       JSON.stringify(a.environment) !== JSON.stringify(b.environment)))) return a;
  const blend = Number.isFinite(amount) ? Math.max(0, Math.min(1, amount)) : 0;
  const yawDelta = Math.atan2(Math.sin(b.yaw_rad - a.yaw_rad), Math.cos(b.yaw_rad - a.yaw_rad));
  const interpolated = { ...(blend >= 1 ? b : a), position: a.position.map((coordinate, axis) => coordinate + (b.position[axis] - coordinate) * blend) as [number, number, number],
    yaw_rad: a.yaw_rad + yawDelta * blend, pitch_rad: a.pitch_rad + (b.pitch_rad - a.pitch_rad) * blend,
    speed_units_s: a.speed_units_s + (b.speed_units_s - a.speed_units_s) * blend };
  if (interpolated.schema_version === 'obs-flight-2') {
    interpolated.ground_contact = interpolated.position[2] === interpolated.environment.ground_z + interpolated.environment.clearance;
  }
  return interpolated;
}
