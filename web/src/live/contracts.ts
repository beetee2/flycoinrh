import Ajv2020 from 'ajv/dist/2020';
import schemas from './generated/schemas.json';
import type * as C from './generated/contracts';

export type * from './generated/contracts';
export type LiveContracts = {
  SourceCapability: C.SourceCapability;
  FrameIdentity: C.FrameIdentity;
  EncoderConfig: C.EncoderConfig;
  NeuralSample: C.NeuralSample;
  FlightControls: C.FlightControls;
  FlightSnapshot: C.FlightSnapshot;
  SyntheticFlightPreview: C.SyntheticFlightPreview;
  SessionConfig: C.SessionConfig;
  SessionStatus: C.SessionStatus;
  StreamEnvelope: C.StreamEnvelope;
  ReplayManifest: C.ReplayManifest;
  LiveHealth: C.LiveHealth;
  LiveConfig: C.LiveConfig;
  StartRequest: C.StartRequest;
  OwnerRequest: C.OwnerRequest;
  PreviewRequest: C.PreviewRequest;
  SourceList: C.SourceList;
  InspectRequest: C.InspectRequest;
  ControlBootstrap: C.ControlBootstrap;
  SourcePreview: C.SourcePreview;
  ApiSnapshot: C.ApiSnapshot;
  ServiceStatus: C.ServiceStatus;
  PreviewReply: C.PreviewReply;
  ReplayPayload: C.ReplayPayload;
  ReplayList: C.ReplayList;
  FlightState: C.FlightState;
};
export type ContractName = keyof LiveContracts;

const ajv = new Ajv2020({ allErrors: true, strict: true, strictNumbers: true, useDefaults: true });
const validators = Object.fromEntries(Object.entries(schemas).map(([name, schema]) => [name, ajv.compile(schema)]));

function requireCondition(condition: boolean, message: string): void {
  if (!condition) throw new Error(`Invalid live contract: ${message}`);
}

function checkSource(source: C.SourceCapability): void {
  if (source.evidence_kind === 'fixture') {
    requireCondition(source.backend === 'synthetic' && source.producer_detection === 'synthetic',
      'fixture sources require the synthetic backend and detection label');
  } else {
    requireCondition(source.backend === 'ffmpeg-v4l2' && source.producer_detection !== 'synthetic',
      'real source metadata cannot describe a synthetic backend or detector');
  }
}

function checkFrame(frame: C.FrameIdentity): void {
  requireCondition((frame.source_clock === 'unknown') === (frame.source_timestamp_ms === null),
    'source timestamp requires an explicit clock; unknown timing must be null');
}

function checkNeural(sample: C.NeuralSample): void {
  checkFrame(sample.frame);
  requireCondition(sample.completed_monotonic_ms >= sample.frame.receipt_monotonic_ms,
    'response completion precedes input receipt');
}

// Pydantic after-validators also run for nested models. Keep these checks aligned
// with flytrap/live/contracts.py and the shared generated compatibility corpus.
function checkSemantics(name: ContractName, value: LiveContracts[ContractName]): void {
  switch (name) {
    case 'SyntheticFlightPreview': {
      const preview = value as C.SyntheticFlightPreview;
      const first = preview.snapshots[0];
      requireCondition(preview.snapshots.every((snapshot, tick) => snapshot.tick === tick &&
        snapshot.evidence_kind === 'fixture' && snapshot.session_id === first.session_id &&
        snapshot.generation === first.generation), 'synthetic preview requires sequential fixture snapshots of one session');
      break;
    }
    case 'SourceCapability':
      checkSource(value as C.SourceCapability);
      break;
    case 'FrameIdentity':
      checkFrame(value as C.FrameIdentity);
      break;
    case 'NeuralSample':
      checkNeural(value as C.NeuralSample);
      break;
    case 'FlightControls': {
      const controls = value as C.FlightControls;
      const lifetime = controls.expires_monotonic_ms - controls.issued_monotonic_ms;
      requireCondition(lifetime >= 0 && lifetime <= 2000, 'control lifetime must be within 2000 ms');
      break;
    }
    case 'ApiSnapshot':
    case 'StreamEnvelope': {
      const stream = value as C.StreamEnvelope | C.ApiSnapshot;
      if (stream.latest_source_frame) checkFrame(stream.latest_source_frame);
      if (stream.neural_sample) checkNeural(stream.neural_sample);
      if (stream.latest_source_frame && stream.neural_sample) {
        requireCondition(stream.latest_source_frame.source_id === stream.neural_sample.frame.source_id,
          'stream frame and neural sample must use the same source');
      }
      for (const item of [stream.latest_source_frame, stream.neural_sample?.frame, stream.flight]) {
        if (item) requireCondition(['session_id', 'generation', 'evidence_kind'].every(key =>
          item[key as keyof typeof item] === stream.status[key as keyof C.SessionStatus]),
        'stream contains a foreign session, generation or evidence kind');
      }
      if (stream.schema_version === 'obs-api-snapshot-1' && stream.last_inferred) {
        checkNeural(stream.last_inferred);
        requireCondition(['session_id', 'generation', 'evidence_kind'].every(key =>
          stream.last_inferred!.frame[key as keyof C.FrameIdentity] === stream.status[key as keyof C.SessionStatus]),
        'foreign historical observation');
      }
      break;
    }
    case 'StartRequest': {
      const start = value as C.StartRequest;
      requireCondition(start.config.recording === start.recording_consent, 'recording requires explicit consent');
      break;
    }
    case 'SourceList':
      (value as C.SourceList).sources.forEach(checkSource);
      break;
    case 'ServiceStatus': {
      const current = (value as C.ServiceStatus).current;
      if (current) checkSemantics('ApiSnapshot', current);
      break;
    }
    case 'PreviewReply': {
      const preview = value as C.PreviewReply;
      if (preview.latest) {
        checkSemantics('SourcePreview', preview.latest);
        requireCondition(['session_id', 'generation', 'evidence_kind'].every(key =>
          preview.latest!.frame[key as keyof C.FrameIdentity] === preview.status[key as keyof C.SessionStatus]),
        'foreign preview frame');
      }
      break;
    }
    case 'SourcePreview': {
      const preview = value as C.SourcePreview;
      checkFrame(preview.frame);
      requireCondition(atob(preview.rgb_base64).length === preview.width*preview.height*3,
        'preview RGB byte count disagrees with dimensions');
      break;
    }
    case 'ReplayList':
      (value as C.ReplayList).recordings.forEach(item => {
        requireCondition([item.manifest, item.state, item.error].filter(v => v != null).length === 1,
          'recording entry requires exactly one manifest, reservation state or error');
        if (item.manifest) checkSemantics('ReplayManifest', item.manifest);
      });
      break;
    case 'ReplayPayload': {
      const replay = value as C.ReplayPayload;
      checkSemantics('ReplayManifest', replay.manifest);
      replay.samples.forEach(checkNeural);
      replay.inputs.forEach(input => checkFrame(input.frame));
      checkSemantics('FlightState', replay.final);
      break;
    }
    case 'FlightState': {
      const state = value as C.FlightState;
      const velocity = state.velocity ?? [0, 0, 0];
      requireCondition(velocity.every(v => typeof v === 'number' && Number.isFinite(v)), 'invalid velocity');
      const speed = Math.hypot(...velocity as [number, number, number]);
      requireCondition(speed <= 6 + 1e-12 && Math.abs(speed-state.snapshot.speed_units_s) <= 1e-9 &&
        Math.abs(state.snapshot.pitch_rad) <= .45 + 1e-12 &&
        (!state.snapshot.neutral || (speed === 0 && (state.yaw_rate ?? 0) === 0)), 'inconsistent bounded flight state');
      break;
    }
    case 'ReplayManifest': {
      const replay = value as C.ReplayManifest;
      checkSource(replay.source);
      requireCondition(replay.config.recording === true, 'replay requires recording consent');
      requireCondition(replay.events_bytes <= (replay.config.recording_max_bytes ?? 33554432),
        'replay exceeds configured recording cap');
      requireCondition(replay.config.source_id === replay.source.source_id, 'replay source must match approved config');
      requireCondition([replay.config, replay.source, replay.initial_flight].every(item =>
        item.evidence_kind === replay.evidence_kind), 'replay evidence labels disagree');
      requireCondition(replay.initial_flight.session_id === replay.session_id &&
        replay.initial_flight.generation === replay.generation && replay.initial_flight.tick === 0,
      'replay initial state must be tick zero of this session generation');
      break;
    }
  }
}

/** Validate untrusted JSON without coercion or mutating the caller's value. */
export function parseLiveContract<K extends ContractName>(name: K, value: unknown): LiveContracts[K] {
  const parsed: unknown = structuredClone(value);
  if (!validators[name](parsed)) throw new Error(`Invalid live ${name} schema.`);
  const checked = parsed as unknown as LiveContracts[K];
  checkSemantics(name, checked);
  return checked;
}
