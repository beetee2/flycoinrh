import { describe, expect, it } from 'vitest';
import examples from '../src/live/generated/examples.json';
import { parseLiveContract } from '../src/live/contracts';
import type { ContractName, LiveContracts } from '../src/live/contracts';

function fixture<K extends ContractName>(name: K): LiveContracts[K] {
  return structuredClone(examples.find(example => example.contract === name && example.valid)!.value) as LiveContracts[K];
}

describe('OBS00 shared Python/TypeScript contract corpus (synthetic)', () => {
  it.each(examples)('$name', example => {
    const parse = () => parseLiveContract(example.contract as ContractName, example.value);
    if (example.valid) expect(parse()).toEqual(example.value);
    else expect(parse).toThrow();
  });
});

describe('OBS00 runtime numeric and nested semantics', () => {
  it.each([NaN, Infinity, -Infinity])('rejects nonfinite runtime numbers: %s', number => {
    const frame = fixture('FrameIdentity');
    frame.receipt_monotonic_ms = number;
    expect(() => parseLiveContract('FrameIdentity', frame)).toThrow();
    const neural = fixture('NeuralSample');
    neural.motor_rates_hz.steer_L = number;
    expect(() => parseLiveContract('NeuralSample', neural)).toThrow();
  });

  it('rejects unknown timing within nested neural and stream inputs', () => {
    const neural = fixture('NeuralSample');
    neural.frame.source_timestamp_ms = 1;
    neural.frame.source_clock = 'unknown';
    expect(() => parseLiveContract('NeuralSample', neural)).toThrow();
    const stream = fixture('StreamEnvelope');
    stream.neural_sample = neural;
    expect(() => parseLiveContract('StreamEnvelope', stream)).toThrow();
    stream.neural_sample = null;
    stream.latest_source_frame = neural.frame;
    expect(() => parseLiveContract('StreamEnvelope', stream)).toThrow();
  });

  it('rejects a nested response completed before receipt', () => {
    const stream = fixture('StreamEnvelope');
    const neural = fixture('NeuralSample');
    neural.completed_monotonic_ms = neural.frame.receipt_monotonic_ms - 1;
    stream.neural_sample = neural;
    expect(() => parseLiveContract('StreamEnvelope', stream)).toThrow();
  });

  it('enforces recording caps and explicit consent inside replay', () => {
    const replay = fixture('ReplayManifest');
    replay.config.recording_max_bytes = 1;
    replay.events_bytes = 2;
    expect(() => parseLiveContract('ReplayManifest', replay)).toThrow();
    replay.events_bytes = 0;
    delete replay.config.recording;
    expect(() => parseLiveContract('ReplayManifest', replay)).toThrow();
  });

  it('fills Python defaults without mutating the caller', () => {
    const input = { source_id: 'fixture-source', evidence_kind: 'fixture', seed: 17 };
    const result = parseLiveContract('SessionConfig', input);
    expect(result.recording).toBe(false);
    expect(result.duration_seconds).toBe(120);
    expect(result.encoder?.size).toBe(16);
    expect(input).not.toHaveProperty('recording');
  });
});
