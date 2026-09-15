import { describe, expect, it } from 'vitest';
import { parseFlightPreview, previewPose } from '../src/live/flightPreview';
import type { FlightSnapshot } from '../src/live/contracts';

const first: FlightSnapshot = { schema_version: 'obs-flight-1', session_id: 'synthetic-preview', generation: 1,
  evidence_kind: 'fixture', tick: 0, position: [0, 0, 0], yaw_rad: 0, pitch_rad: 0, speed_units_s: 0,
  applied_response_id: null, neutral: true };
export function fixturePreview() {
  return { schema_version: 'obs-flight-preview-1' as const, evidence_kind: 'synthetic' as const, dt_ms: 20 as const,
    snapshots: Array.from({ length: 101 }, (_, tick) => ({ ...first, tick, position: [tick * 0.1, tick * 0.03, 0] as [number, number, number],
      yaw_rad: tick * 0.01, speed_units_s: tick === 0 ? 0 : 5, neutral: tick === 0 })) };
}

describe('synthetic presentation boundary', () => {
  it('accepts a fixture sequence without mutating input', () => {
    const fixture = fixturePreview(), before = structuredClone(fixture);
    expect(parseFlightPreview(fixture).snapshots).toHaveLength(101);
    expect(fixture).toEqual(before);
  });
  it.each([
    (p: any) => { p.extra = true; },
    (p: any) => { p.evidence_kind = 'real'; },
    (p: any) => { p.schema_version = 'unknown'; },
    (p: any) => { p.dt_ms = 16; },
    (p: any) => { p.snapshots = []; },
    (p: any) => { p.snapshots[1].position = [NaN, 0, 0]; },
    (p: any) => { delete p.snapshots[1].yaw_rad; },
    (p: any) => { p.snapshots[1].tick = 2; },
    (p: any) => { p.snapshots[1].evidence_kind = 'real'; },
    (p: any) => { p.snapshots[1].session_id = 'foreign-session'; },
    (p: any) => { p.snapshots[1].generation = 2; },
  ])('rejects malformed, mislabeled, or discontinuous payloads', mutate => {
    const fixture = fixturePreview(); mutate(fixture);
    expect(() => parseFlightPreview(fixture)).toThrow(/Invalid/);
  });
  it('interpolates existing snapshots independently of prior display calls and clamps replay boundaries', () => {
    const preview = parseFlightPreview(fixturePreview());
    const pose = previewPose(preview, 1050);
    expect(pose.position[0]).toBeCloseTo(5.25);
    for (let t = 0; t < 1050; t += 1000 / 144) previewPose(preview, t);
    expect(previewPose(preview, 1050)).toEqual(pose);
    expect(previewPose(preview, -100).position).toEqual(preview.snapshots[0].position);
    expect(previewPose(preview, 50000).position).toEqual(preview.snapshots.at(-1)!.position);
  });
  it('takes the short angular path when yaw wraps', () => {
    const preview = fixturePreview(); preview.snapshots[0].yaw_rad = Math.PI - 0.1; preview.snapshots[1].yaw_rad = -Math.PI + 0.1;
    expect(previewPose(preview, 10).yaw_rad).toBeCloseTo(Math.PI);
  });
});
