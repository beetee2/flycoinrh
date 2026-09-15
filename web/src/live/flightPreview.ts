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
  const yawDelta = Math.atan2(Math.sin(b.yaw_rad - a.yaw_rad), Math.cos(b.yaw_rad - a.yaw_rad));
  return { ...a, position: a.position.map((coordinate, axis) => coordinate + (b.position[axis] - coordinate) * blend) as [number, number, number],
    yaw_rad: a.yaw_rad + yawDelta * blend, pitch_rad: a.pitch_rad + (b.pitch_rad - a.pitch_rad) * blend,
    speed_units_s: a.speed_units_s + (b.speed_units_s - a.speed_units_s) * blend };
}
