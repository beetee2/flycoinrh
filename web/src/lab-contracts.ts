import Ajv2020 from 'ajv/dist/2020';
import addFormats from 'ajv-formats';
import schema from './generated/lab-result.schema.json';

export const MOTORS = ['steer_L', 'steer_R', 'fwd_L', 'fwd_R', 'back', 'stop', 'click'] as const;
export type Motor = typeof MOTORS[number];
export type Pixels = number[];
export type LabStatus = { state: 'ready' | 'busy' | 'unavailable'; message: string; attempted_calls: number; call_cap: number; seeds: number[]; calls_per_comparison: number };
export type Population = { neuron_indices: number[]; body_ids: (string | number)[]; pixel_indices: number[]; sampled_pixels_u8: number[]; drive_hz: number[]; coverage_counts: number[]; missing_coordinates: number };
export type Retina = { populations: { L1: Population; L2: Population }; union_coverage_counts: number[]; sampled_pixel_count: number; discarded_pixel_indices: number[] };
export type LabResult = {
  schema_version: 'flytrap-lab-result-1'; result_id: string; created_at: string; cached: boolean; fixture: boolean;
  request: { schema_version: 'flytrap-lab-request-1'; a: Pixels; b: Pixels }; seeds: number[];
  samples: { side: 'A' | 'A_repeat' | 'B'; seed: number; motor_rates_hz: Record<Motor, number>; statistics: Record<string, number>; neural_ms: number }[];
  retina: { A: Retina; B: Retina };
  comparison: { same_image: boolean; equal_brightness: boolean; mean_brightness_u8: { A: number; B: number }; same_seed_repeatable: boolean; motor_rates_hz: Record<Motor, { a_mean: number; b_mean: number; a_sd: number; b_sd: number; delta_mean: number; delta_sd: number; paired_deltas: number[] }> };
  identities: Record<string, unknown>; attempted_calls: number;
};
const ajv = new Ajv2020({ allErrors: true, strict: true, strictNumbers: true });
addFormats(ajv);
const validate = ajv.compile(schema);
export function parseLabResult(value: unknown): LabResult {
  if (!validate(value)) throw new Error('Invalid result schema. No result was displayed.');
  const r = value as LabResult;
  const expected = [17,29,43].flatMap(seed => ['A','A_repeat','B'].map(side => `${seed}:${side}`));
  if (JSON.stringify(r.seeds) !== '[17,29,43]' || r.samples.some((s,i) => `${s.seed}:${s.side}` !== expected[i])) throw new Error('Invalid matched seed sample order.');
  for (const side of ['A','B'] as const) {
    for (const pop of Object.values(r.retina[side].populations)) {
      if ([pop.body_ids,pop.pixel_indices,pop.sampled_pixels_u8,pop.drive_hz].some(v => v.length !== pop.neuron_indices.length)) throw new Error('Invalid retinal array alignment.');
    }
  }
  return r;
}
export function parseLabStatus(value: unknown): LabStatus {
  const s = value as LabStatus;
  if (!s || !['ready', 'busy', 'unavailable'].includes(s.state) || typeof s.message !== 'string' ||
      !Number.isInteger(s.attempted_calls) || s.attempted_calls < 0 || s.call_cap !== 256 ||
      s.calls_per_comparison !== 9 || JSON.stringify(s.seeds) !== '[17,29,43]') throw new Error('Invalid service status.');
  return s;
}
export function preset(name: string): Pixels {
  return Array.from({ length: 256 }, (_, i) => name === 'White' ? 255 : name === 'Vertical stripes' ? (i % 16 % 2) * 255 : name === 'Horizontal stripes' ? (Math.floor(i / 16) % 2) * 255 : name === 'Checkerboard' ? ((i % 16 + Math.floor(i / 16)) % 2) * 255 : 0);
}
