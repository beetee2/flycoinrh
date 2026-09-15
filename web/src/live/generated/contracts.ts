// Generated from flytrap/live/contracts.py JSON Schemas. Do not edit.
export namespace SourceCapabilityContract {
export type SchemaVersion = "obs-source-1";
export type SourceId = string;
export type EvidenceKind = "real" | "fixture";
export type Name = string;
export type Driver = string | null;
export type Backend = "ffmpeg-v4l2" | "synthetic";
export type Capabilities =
  | []
  | ["video_capture" | "streaming" | "readwrite"]
  | ["video_capture" | "streaming" | "readwrite", "video_capture" | "streaming" | "readwrite"]
  | [
      "video_capture" | "streaming" | "readwrite",
      "video_capture" | "streaming" | "readwrite",
      "video_capture" | "streaming" | "readwrite"
    ]
  | null;
export type Formats = SourceFormat[] | null;
export type PixelFormat = "RGB24" | "BGR24" | "YUYV" | "NV12" | "MJPEG";
export type Width = number;
export type Height = number;
export type Fps = number;
export type MetadataState = "available" | "partial" | "unavailable";
export type ProducerDetection = "unknown" | "driver" | "obs_readonly_monitor" | "synthetic";

export interface SourceCapability {
  schema_version: SchemaVersion;
  source_id: SourceId;
  evidence_kind: EvidenceKind;
  name: Name;
  driver: Driver;
  backend: Backend;
  capabilities: Capabilities;
  formats: Formats;
  metadata_state: MetadataState;
  producer_detection: ProducerDetection;
}
export interface SourceFormat {
  pixel_format: PixelFormat;
  width: Width;
  height: Height;
  fps: Fps;
}

}
export type SourceCapability = SourceCapabilityContract.SourceCapability;

export namespace FrameIdentityContract {
export type SchemaVersion = "obs-frame-1";
export type SourceId = string;
export type SessionId = string;
export type Generation = number;
export type Sequence = number;
export type EvidenceKind = "real" | "fixture";
export type Width = number;
export type Height = number;
export type PixelFormat = "RGB24";
export type ReceiptMonotonicMs = number;
export type SourceTimestampMs = number | null;
export type SourceSequence = number | null;
export type SourceClock = "unknown" | "producer" | "local_monotonic";

export interface FrameIdentity {
  schema_version: SchemaVersion;
  source_id: SourceId;
  session_id: SessionId;
  generation: Generation;
  sequence: Sequence;
  evidence_kind: EvidenceKind;
  width: Width;
  height: Height;
  pixel_format: PixelFormat;
  receipt_monotonic_ms: ReceiptMonotonicMs;
  source_timestamp_ms: SourceTimestampMs;
  source_sequence: SourceSequence;
  source_clock: SourceClock;
}

}
export type FrameIdentity = FrameIdentityContract.FrameIdentity;

export namespace EncoderConfigContract {
export type SchemaVersion = "obs-encoder-1";
export type EncoderId = "obs-rgb-letterbox16-v1";
export type Size = 16;
export type Grayscale = "(77R+150G+29B+128)//256";
export type Resampler = "nearest-pixel-center";
export type PaddingU8 = 0;
export type Color = "full-range-rgb-bt601-conversion";

export interface EncoderConfig {
  schema_version?: SchemaVersion;
  encoder_id?: EncoderId;
  size?: Size;
  grayscale?: Grayscale;
  resampler?: Resampler;
  padding_u8?: PaddingU8;
  color?: Color;
}

}
export type EncoderConfig = EncoderConfigContract.EncoderConfig;

export namespace NeuralSampleContract {
export type SchemaVersion = "obs-neural-1";
export type ResponseId = string;
export type SchemaVersion1 = "obs-frame-1";
export type SourceId = string;
export type SessionId = string;
export type Generation = number;
export type Sequence = number;
export type EvidenceKind = "real" | "fixture";
export type Width = number;
export type Height = number;
export type PixelFormat = "RGB24";
export type ReceiptMonotonicMs = number;
export type SourceTimestampMs = number | null;
export type SourceSequence = number | null;
export type SourceClock = "unknown" | "producer" | "local_monotonic";
/**
 * @minItems 256
 * @maxItems 256
 */
export type ObservationU8 = [
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number
];
export type EncoderId = "obs-rgb-letterbox16-v1";
export type ModelId = string;
export type StepIndex = number;
export type CompletedMonotonicMs = number;
export type NeuralMs = 20;
export type NeuralStateMode = "windowed_reset";
export type SteerL = number;
export type SteerR = number;
export type FwdL = number;
export type FwdR = number;
export type Back = number;
export type Stop = number;
export type Click = number;
export type Dx = number;
export type Dy = number;
export type Click1 = boolean;

export interface NeuralSample {
  schema_version: SchemaVersion;
  response_id: ResponseId;
  frame: FrameIdentity;
  observation_u8: ObservationU8;
  encoder_id: EncoderId;
  model_id: ModelId;
  step_index: StepIndex;
  completed_monotonic_ms: CompletedMonotonicMs;
  neural_ms: NeuralMs;
  neural_state_mode: NeuralStateMode;
  motor_rates_hz: MotorRates;
  raw_action: RawAction;
}
export interface FrameIdentity {
  schema_version: SchemaVersion1;
  source_id: SourceId;
  session_id: SessionId;
  generation: Generation;
  sequence: Sequence;
  evidence_kind: EvidenceKind;
  width: Width;
  height: Height;
  pixel_format: PixelFormat;
  receipt_monotonic_ms: ReceiptMonotonicMs;
  source_timestamp_ms: SourceTimestampMs;
  source_sequence: SourceSequence;
  source_clock: SourceClock;
}
export interface MotorRates {
  steer_L: SteerL;
  steer_R: SteerR;
  fwd_L: FwdL;
  fwd_R: FwdR;
  back: Back;
  stop: Stop;
  click: Click;
}
export interface RawAction {
  dx: Dx;
  dy: Dy;
  click: Click1;
}

}
export type NeuralSample = NeuralSampleContract.NeuralSample;

export namespace FlightControlsContract {
export type SchemaVersion = "obs-controls-1";
export type DecoderId = "motor-flight-v1";
export type ResponseId = string;
export type SessionId = string;
export type Generation = number;
export type EvidenceKind = "real" | "fixture";
export type IssuedMonotonicMs = number;
export type ExpiresMonotonicMs = number;
export type YawRateRadS = number;
export type PitchTargetRad = number;
export type SpeedTargetUnitsS = number;

/**
 * Decoder output only; source pixels and world targets are excluded.
 */
export interface FlightControls {
  schema_version: SchemaVersion;
  decoder_id: DecoderId;
  response_id: ResponseId;
  session_id: SessionId;
  generation: Generation;
  evidence_kind: EvidenceKind;
  issued_monotonic_ms: IssuedMonotonicMs;
  expires_monotonic_ms: ExpiresMonotonicMs;
  yaw_rate_rad_s: YawRateRadS;
  pitch_target_rad: PitchTargetRad;
  speed_target_units_s: SpeedTargetUnitsS;
}

}
export type FlightControls = FlightControlsContract.FlightControls;

export namespace FlightSnapshotContract {
export type SchemaVersion = "obs-flight-1";
export type SessionId = string;
export type Generation = number;
export type EvidenceKind = "real" | "fixture";
export type Tick = number;
/**
 * @minItems 3
 * @maxItems 3
 */
export type Position = [number, number, number];
export type YawRad = number;
export type PitchRad = number;
export type SpeedUnitsS = number;
export type AppliedResponseId = string | null;
export type Neutral = boolean;

export interface FlightSnapshot {
  schema_version: SchemaVersion;
  session_id: SessionId;
  generation: Generation;
  evidence_kind: EvidenceKind;
  tick: Tick;
  position: Position;
  yaw_rad: YawRad;
  pitch_rad: PitchRad;
  speed_units_s: SpeedUnitsS;
  applied_response_id: AppliedResponseId;
  neutral: Neutral;
}

}
export type FlightSnapshot = FlightSnapshotContract.FlightSnapshot;

export namespace SyntheticFlightPreviewContract {
export type SchemaVersion = "obs-flight-preview-1";
export type EvidenceKind = "synthetic";
export type DtMs = 20;
/**
 * @minItems 2
 * @maxItems 601
 */
export type Snapshots = [FlightSnapshot, FlightSnapshot, ...FlightSnapshot[]];
export type SchemaVersion1 = "obs-flight-1";
export type SessionId = string;
export type Generation = number;
export type EvidenceKind1 = "real" | "fixture";
export type Tick = number;
/**
 * @minItems 3
 * @maxItems 3
 */
export type Position = [number, number, number];
export type YawRad = number;
export type PitchRad = number;
export type SpeedUnitsS = number;
export type AppliedResponseId = string | null;
export type Neutral = boolean;

export interface SyntheticFlightPreview {
  schema_version: SchemaVersion;
  evidence_kind: EvidenceKind;
  dt_ms: DtMs;
  snapshots: Snapshots;
}
export interface FlightSnapshot {
  schema_version: SchemaVersion1;
  session_id: SessionId;
  generation: Generation;
  evidence_kind: EvidenceKind1;
  tick: Tick;
  position: Position;
  yaw_rad: YawRad;
  pitch_rad: PitchRad;
  speed_units_s: SpeedUnitsS;
  applied_response_id: AppliedResponseId;
  neutral: Neutral;
}

}
export type SyntheticFlightPreview = SyntheticFlightPreviewContract.SyntheticFlightPreview;

export namespace SessionConfigContract {
export type SchemaVersion = "obs-session-config-1";
export type SourceId = string;
export type EvidenceKind = "real" | "fixture";
export type Seed = number;
export type Recording = boolean;
export type DurationSeconds = number;
export type MaxModelCalls = number;
export type SourceDeadlineMs = number;
export type StepDeadlineMs = number;
export type StartupDeadlineMs = number;
export type ResponseMaxAgeMs = number;
export type LeaseMs = number;
export type StopGraceMs = number;
export type RecordingMaxBytes = number;
export type FixedStepMs = 20;
export type SchemaVersion1 = "obs-encoder-1";
export type EncoderId = "obs-rgb-letterbox16-v1";
export type Size = 16;
export type Grayscale = "(77R+150G+29B+128)//256";
export type Resampler = "nearest-pixel-center";
export type PaddingU8 = 0;
export type Color = "full-range-rgb-bt601-conversion";
export type DecoderId = "motor-flight-v1";
export type NeuralStateMode = "windowed_reset";
export type LearningEnabled = false;

export interface SessionConfig {
  schema_version?: SchemaVersion;
  source_id: SourceId;
  evidence_kind: EvidenceKind;
  seed: Seed;
  recording?: Recording;
  duration_seconds?: DurationSeconds;
  max_model_calls?: MaxModelCalls;
  source_deadline_ms?: SourceDeadlineMs;
  step_deadline_ms?: StepDeadlineMs;
  startup_deadline_ms?: StartupDeadlineMs;
  response_max_age_ms?: ResponseMaxAgeMs;
  lease_ms?: LeaseMs;
  stop_grace_ms?: StopGraceMs;
  recording_max_bytes?: RecordingMaxBytes;
  fixed_step_ms?: FixedStepMs;
  encoder?: EncoderConfig;
  decoder_id?: DecoderId;
  neural_state_mode?: NeuralStateMode;
  learning_enabled?: LearningEnabled;
}
export interface EncoderConfig {
  schema_version?: SchemaVersion1;
  encoder_id?: EncoderId;
  size?: Size;
  grayscale?: Grayscale;
  resampler?: Resampler;
  padding_u8?: PaddingU8;
  color?: Color;
}

}
export type SessionConfig = SessionConfigContract.SessionConfig;

export namespace SessionStatusContract {
export type SchemaVersion = "obs-session-status-1";
export type SessionId = string;
export type Generation = number;
export type EvidenceKind = "real" | "fixture";
export type State =
  "idle" | "previewing" | "starting" | "running" | "stopping" | "stopped" | "source_lost" | "failed" | "limit_reached";
export type Reason = string | null;
export type AttemptedCalls = number;
export type AcceptedFrames = number;
export type OverwrittenFrames = number;
export type ContentUnchangedMs = number;
export type ProducerHealth = "unknown" | "active" | "inactive";
export type LastFrameSequence = number | null;
export type LastResponseId = string | null;

export interface SessionStatus {
  schema_version: SchemaVersion;
  session_id: SessionId;
  generation: Generation;
  evidence_kind: EvidenceKind;
  state: State;
  reason: Reason;
  attempted_calls: AttemptedCalls;
  accepted_frames: AcceptedFrames;
  overwritten_frames: OverwrittenFrames;
  content_unchanged_ms: ContentUnchangedMs;
  producer_health: ProducerHealth;
  last_frame_sequence: LastFrameSequence;
  last_response_id: LastResponseId;
}

}
export type SessionStatus = SessionStatusContract.SessionStatus;

export namespace StreamEnvelopeContract {
export type SchemaVersion = "obs-stream-1";
export type EventSequence = number;
export type SentMonotonicMs = number;
export type SchemaVersion1 = "obs-session-status-1";
export type SessionId = string;
export type Generation = number;
export type EvidenceKind = "real" | "fixture";
export type State =
  "idle" | "previewing" | "starting" | "running" | "stopping" | "stopped" | "source_lost" | "failed" | "limit_reached";
export type Reason = string | null;
export type AttemptedCalls = number;
export type AcceptedFrames = number;
export type OverwrittenFrames = number;
export type ContentUnchangedMs = number;
export type ProducerHealth = "unknown" | "active" | "inactive";
export type LastFrameSequence = number | null;
export type LastResponseId = string | null;
export type SchemaVersion2 = "obs-frame-1";
export type SourceId = string;
export type SessionId1 = string;
export type Generation1 = number;
export type Sequence = number;
export type EvidenceKind1 = "real" | "fixture";
export type Width = number;
export type Height = number;
export type PixelFormat = "RGB24";
export type ReceiptMonotonicMs = number;
export type SourceTimestampMs = number | null;
export type SourceSequence = number | null;
export type SourceClock = "unknown" | "producer" | "local_monotonic";
export type SchemaVersion3 = "obs-neural-1";
export type ResponseId = string;
/**
 * @minItems 256
 * @maxItems 256
 */
export type ObservationU8 = [
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number
];
export type EncoderId = "obs-rgb-letterbox16-v1";
export type ModelId = string;
export type StepIndex = number;
export type CompletedMonotonicMs = number;
export type NeuralMs = 20;
export type NeuralStateMode = "windowed_reset";
export type SteerL = number;
export type SteerR = number;
export type FwdL = number;
export type FwdR = number;
export type Back = number;
export type Stop = number;
export type Click = number;
export type Dx = number;
export type Dy = number;
export type Click1 = boolean;
export type SchemaVersion4 = "obs-flight-1";
export type SessionId2 = string;
export type Generation2 = number;
export type EvidenceKind2 = "real" | "fixture";
export type Tick = number;
/**
 * @minItems 3
 * @maxItems 3
 */
export type Position = [number, number, number];
export type YawRad = number;
export type PitchRad = number;
export type SpeedUnitsS = number;
export type AppliedResponseId = string | null;
export type Neutral = boolean;

export interface StreamEnvelope {
  schema_version: SchemaVersion;
  event_sequence: EventSequence;
  sent_monotonic_ms: SentMonotonicMs;
  status: SessionStatus;
  latest_source_frame: FrameIdentity | null;
  neural_sample: NeuralSample | null;
  flight: FlightSnapshot | null;
}
export interface SessionStatus {
  schema_version: SchemaVersion1;
  session_id: SessionId;
  generation: Generation;
  evidence_kind: EvidenceKind;
  state: State;
  reason: Reason;
  attempted_calls: AttemptedCalls;
  accepted_frames: AcceptedFrames;
  overwritten_frames: OverwrittenFrames;
  content_unchanged_ms: ContentUnchangedMs;
  producer_health: ProducerHealth;
  last_frame_sequence: LastFrameSequence;
  last_response_id: LastResponseId;
}
export interface FrameIdentity {
  schema_version: SchemaVersion2;
  source_id: SourceId;
  session_id: SessionId1;
  generation: Generation1;
  sequence: Sequence;
  evidence_kind: EvidenceKind1;
  width: Width;
  height: Height;
  pixel_format: PixelFormat;
  receipt_monotonic_ms: ReceiptMonotonicMs;
  source_timestamp_ms: SourceTimestampMs;
  source_sequence: SourceSequence;
  source_clock: SourceClock;
}
export interface NeuralSample {
  schema_version: SchemaVersion3;
  response_id: ResponseId;
  frame: FrameIdentity;
  observation_u8: ObservationU8;
  encoder_id: EncoderId;
  model_id: ModelId;
  step_index: StepIndex;
  completed_monotonic_ms: CompletedMonotonicMs;
  neural_ms: NeuralMs;
  neural_state_mode: NeuralStateMode;
  motor_rates_hz: MotorRates;
  raw_action: RawAction;
}
export interface MotorRates {
  steer_L: SteerL;
  steer_R: SteerR;
  fwd_L: FwdL;
  fwd_R: FwdR;
  back: Back;
  stop: Stop;
  click: Click;
}
export interface RawAction {
  dx: Dx;
  dy: Dy;
  click: Click1;
}
export interface FlightSnapshot {
  schema_version: SchemaVersion4;
  session_id: SessionId2;
  generation: Generation2;
  evidence_kind: EvidenceKind2;
  tick: Tick;
  position: Position;
  yaw_rad: YawRad;
  pitch_rad: PitchRad;
  speed_units_s: SpeedUnitsS;
  applied_response_id: AppliedResponseId;
  neutral: Neutral;
}

}
export type StreamEnvelope = StreamEnvelopeContract.StreamEnvelope;

export namespace ReplayManifestContract {
export type SchemaVersion = "obs-replay-1";
export type SessionId = string;
export type Generation = number;
export type EvidenceKind = "real" | "fixture";
export type State = "partial" | "aborted" | "complete";
export type SchemaVersion1 = "obs-session-config-1";
export type SourceId = string;
export type EvidenceKind1 = "real" | "fixture";
export type Seed = number;
export type Recording = boolean;
export type DurationSeconds = number;
export type MaxModelCalls = number;
export type SourceDeadlineMs = number;
export type StepDeadlineMs = number;
export type StartupDeadlineMs = number;
export type ResponseMaxAgeMs = number;
export type LeaseMs = number;
export type StopGraceMs = number;
export type RecordingMaxBytes = number;
export type FixedStepMs = 20;
export type SchemaVersion2 = "obs-encoder-1";
export type EncoderId = "obs-rgb-letterbox16-v1";
export type Size = 16;
export type Grayscale = "(77R+150G+29B+128)//256";
export type Resampler = "nearest-pixel-center";
export type PaddingU8 = 0;
export type Color = "full-range-rgb-bt601-conversion";
export type DecoderId = "motor-flight-v1";
export type NeuralStateMode = "windowed_reset";
export type LearningEnabled = false;
export type SchemaVersion3 = "obs-source-1";
export type SourceId1 = string;
export type EvidenceKind2 = "real" | "fixture";
export type Name = string;
export type Driver = string | null;
export type Backend = "ffmpeg-v4l2" | "synthetic";
export type Capabilities =
  | []
  | ["video_capture" | "streaming" | "readwrite"]
  | ["video_capture" | "streaming" | "readwrite", "video_capture" | "streaming" | "readwrite"]
  | [
      "video_capture" | "streaming" | "readwrite",
      "video_capture" | "streaming" | "readwrite",
      "video_capture" | "streaming" | "readwrite"
    ]
  | null;
export type Formats = SourceFormat[] | null;
export type PixelFormat = "RGB24" | "BGR24" | "YUYV" | "NV12" | "MJPEG";
export type Width = number;
export type Height = number;
export type Fps = number;
export type MetadataState = "available" | "partial" | "unavailable";
export type ProducerDetection = "unknown" | "driver" | "obs_readonly_monitor" | "synthetic";
export type SchemaVersion4 = "obs-flight-1";
export type SessionId1 = string;
export type Generation1 = number;
export type EvidenceKind3 = "real" | "fixture";
export type Tick = number;
/**
 * @minItems 3
 * @maxItems 3
 */
export type Position = [number, number, number];
export type YawRad = number;
export type PitchRad = number;
export type SpeedUnitsS = number;
export type AppliedResponseId = string | null;
export type Neutral = boolean;
export type SourceHead = string;
export type SourceTreeSha256 = string;
export type GraphSha256 = string;
export type AnnotationsSha256 = string;
export type CheckpointSha256 = string;
export type ModelSourceSha256 = string;
export type ModelConfigSha256 = string;
export type BackendVersion = string;
export type PythonVersion = string;
export type NumpyVersion = string;
export type ScipyVersion = string;
export type ModelId = string;
export type NeuralStateMode1 = "windowed_reset";
export type Gains = "all-one-float32";
export type LearningEnabled1 = false;
export type EventsSha256 = string;
export type EventCount = number;
export type EventsBytes = number;
export type EventsFile = "events.jsonl";

export interface ReplayManifest {
  schema_version: SchemaVersion;
  session_id: SessionId;
  generation: Generation;
  evidence_kind: EvidenceKind;
  state: State;
  config: SessionConfig;
  source: SourceCapability;
  initial_flight: FlightSnapshot;
  provenance: Provenance;
  events_sha256: EventsSha256;
  event_count: EventCount;
  events_bytes: EventsBytes;
  events_file: EventsFile;
}
export interface SessionConfig {
  schema_version?: SchemaVersion1;
  source_id: SourceId;
  evidence_kind: EvidenceKind1;
  seed: Seed;
  recording?: Recording;
  duration_seconds?: DurationSeconds;
  max_model_calls?: MaxModelCalls;
  source_deadline_ms?: SourceDeadlineMs;
  step_deadline_ms?: StepDeadlineMs;
  startup_deadline_ms?: StartupDeadlineMs;
  response_max_age_ms?: ResponseMaxAgeMs;
  lease_ms?: LeaseMs;
  stop_grace_ms?: StopGraceMs;
  recording_max_bytes?: RecordingMaxBytes;
  fixed_step_ms?: FixedStepMs;
  encoder?: EncoderConfig;
  decoder_id?: DecoderId;
  neural_state_mode?: NeuralStateMode;
  learning_enabled?: LearningEnabled;
}
export interface EncoderConfig {
  schema_version?: SchemaVersion2;
  encoder_id?: EncoderId;
  size?: Size;
  grayscale?: Grayscale;
  resampler?: Resampler;
  padding_u8?: PaddingU8;
  color?: Color;
}
export interface SourceCapability {
  schema_version: SchemaVersion3;
  source_id: SourceId1;
  evidence_kind: EvidenceKind2;
  name: Name;
  driver: Driver;
  backend: Backend;
  capabilities: Capabilities;
  formats: Formats;
  metadata_state: MetadataState;
  producer_detection: ProducerDetection;
}
export interface SourceFormat {
  pixel_format: PixelFormat;
  width: Width;
  height: Height;
  fps: Fps;
}
export interface FlightSnapshot {
  schema_version: SchemaVersion4;
  session_id: SessionId1;
  generation: Generation1;
  evidence_kind: EvidenceKind3;
  tick: Tick;
  position: Position;
  yaw_rad: YawRad;
  pitch_rad: PitchRad;
  speed_units_s: SpeedUnitsS;
  applied_response_id: AppliedResponseId;
  neutral: Neutral;
}
export interface Provenance {
  source_head: SourceHead;
  source_tree_sha256: SourceTreeSha256;
  graph_sha256: GraphSha256;
  annotations_sha256: AnnotationsSha256;
  checkpoint_sha256: CheckpointSha256;
  model_source_sha256: ModelSourceSha256;
  model_config_sha256: ModelConfigSha256;
  backend_version: BackendVersion;
  python_version: PythonVersion;
  numpy_version: NumpyVersion;
  scipy_version: ScipyVersion;
  model_id: ModelId;
  neural_state_mode: NeuralStateMode1;
  gains: Gains;
  learning_enabled: LearningEnabled1;
}

}
export type ReplayManifest = ReplayManifestContract.ReplayManifest;

export namespace LiveHealthContract {
export type SchemaVersion = "obs-health-1";
export type Status = "ok";
export type Phase = "OBS04";
export type State = "available";
export type CaptureImplemented = true;
export type InferenceImplemented = true;

export interface LiveHealth {
  schema_version?: SchemaVersion;
  status?: Status;
  phase?: Phase;
  state?: State;
  capture_implemented?: CaptureImplemented;
  inference_implemented?: InferenceImplemented;
}

}
export type LiveHealth = LiveHealthContract.LiveHealth;

export namespace LiveConfigContract {
export type SchemaVersion = "obs-config-1";
export type Phase = "OBS04";
export type CaptureImplemented = true;
export type InferenceImplemented = true;
export type RecordingDefault = false;
export type SourceSelectionRequired = true;
export type ValidationCallCap = 1024;
export type Backend = "ffmpeg-v4l2";
export type SchemaVersion1 = "obs-encoder-1";
export type EncoderId = "obs-rgb-letterbox16-v1";
export type Size = 16;
export type Grayscale = "(77R+150G+29B+128)//256";
export type Resampler = "nearest-pixel-center";
export type PaddingU8 = 0;
export type Color = "full-range-rgb-bt601-conversion";

export interface LiveConfig {
  schema_version?: SchemaVersion;
  phase?: Phase;
  capture_implemented?: CaptureImplemented;
  inference_implemented?: InferenceImplemented;
  recording_default?: RecordingDefault;
  source_selection_required?: SourceSelectionRequired;
  validation_call_cap?: ValidationCallCap;
  backend?: Backend;
  encoder?: EncoderConfig;
}
export interface EncoderConfig {
  schema_version?: SchemaVersion1;
  encoder_id?: EncoderId;
  size?: Size;
  grayscale?: Grayscale;
  resampler?: Resampler;
  padding_u8?: PaddingU8;
  color?: Color;
}

}
export type LiveConfig = LiveConfigContract.LiveConfig;

export namespace StartRequestContract {
export type SchemaVersion = "obs-start-1";
export type RequestId = string;
export type OwnerToken = string;
export type SchemaVersion1 = "obs-session-config-1";
export type SourceId = string;
export type EvidenceKind = "real" | "fixture";
export type Seed = number;
export type Recording = boolean;
export type DurationSeconds = number;
export type MaxModelCalls = number;
export type SourceDeadlineMs = number;
export type StepDeadlineMs = number;
export type StartupDeadlineMs = number;
export type ResponseMaxAgeMs = number;
export type LeaseMs = number;
export type StopGraceMs = number;
export type RecordingMaxBytes = number;
export type FixedStepMs = 20;
export type SchemaVersion2 = "obs-encoder-1";
export type EncoderId = "obs-rgb-letterbox16-v1";
export type Size = 16;
export type Grayscale = "(77R+150G+29B+128)//256";
export type Resampler = "nearest-pixel-center";
export type PaddingU8 = 0;
export type Color = "full-range-rgb-bt601-conversion";
export type DecoderId = "motor-flight-v1";
export type NeuralStateMode = "windowed_reset";
export type LearningEnabled = false;
export type RecordingConsent = boolean;

export interface StartRequest {
  schema_version?: SchemaVersion;
  request_id: RequestId;
  owner_token: OwnerToken;
  config: SessionConfig;
  recording_consent?: RecordingConsent;
}
export interface SessionConfig {
  schema_version?: SchemaVersion1;
  source_id: SourceId;
  evidence_kind: EvidenceKind;
  seed: Seed;
  recording?: Recording;
  duration_seconds?: DurationSeconds;
  max_model_calls?: MaxModelCalls;
  source_deadline_ms?: SourceDeadlineMs;
  step_deadline_ms?: StepDeadlineMs;
  startup_deadline_ms?: StartupDeadlineMs;
  response_max_age_ms?: ResponseMaxAgeMs;
  lease_ms?: LeaseMs;
  stop_grace_ms?: StopGraceMs;
  recording_max_bytes?: RecordingMaxBytes;
  fixed_step_ms?: FixedStepMs;
  encoder?: EncoderConfig;
  decoder_id?: DecoderId;
  neural_state_mode?: NeuralStateMode;
  learning_enabled?: LearningEnabled;
}
export interface EncoderConfig {
  schema_version?: SchemaVersion2;
  encoder_id?: EncoderId;
  size?: Size;
  grayscale?: Grayscale;
  resampler?: Resampler;
  padding_u8?: PaddingU8;
  color?: Color;
}

}
export type StartRequest = StartRequestContract.StartRequest;

export namespace OwnerRequestContract {
export type Generation = number;
export type OwnerToken = string;

export interface OwnerRequest {
  generation: Generation;
  owner_token: OwnerToken;
}

}
export type OwnerRequest = OwnerRequestContract.OwnerRequest;

export namespace PreviewRequestContract {
export type SchemaVersion = "obs-preview-request-1";
export type RequestId = string;
export type OwnerToken = string;
export type SourceId = string;
export type DurationSeconds = number;

export interface PreviewRequest {
  schema_version?: SchemaVersion;
  request_id: RequestId;
  owner_token: OwnerToken;
  source_id: SourceId;
  duration_seconds?: DurationSeconds;
}

}
export type PreviewRequest = PreviewRequestContract.PreviewRequest;

export namespace SourceListContract {
export type SchemaVersion = "obs-sources-1";
export type SchemaVersion1 = "obs-source-1";
export type SourceId = string;
export type EvidenceKind = "real" | "fixture";
export type Name = string;
export type Driver = string | null;
export type Backend = "ffmpeg-v4l2" | "synthetic";
export type Capabilities =
  | []
  | ["video_capture" | "streaming" | "readwrite"]
  | ["video_capture" | "streaming" | "readwrite", "video_capture" | "streaming" | "readwrite"]
  | [
      "video_capture" | "streaming" | "readwrite",
      "video_capture" | "streaming" | "readwrite",
      "video_capture" | "streaming" | "readwrite"
    ]
  | null;
export type Formats = SourceFormat[] | null;
export type PixelFormat = "RGB24" | "BGR24" | "YUYV" | "NV12" | "MJPEG";
export type Width = number;
export type Height = number;
export type Fps = number;
export type MetadataState = "available" | "partial" | "unavailable";
export type ProducerDetection = "unknown" | "driver" | "obs_readonly_monitor" | "synthetic";
/**
 * @maxItems 128
 */
export type Sources = SourceCapability[];

export interface SourceList {
  schema_version?: SchemaVersion;
  sources: Sources;
}
export interface SourceCapability {
  schema_version: SchemaVersion1;
  source_id: SourceId;
  evidence_kind: EvidenceKind;
  name: Name;
  driver: Driver;
  backend: Backend;
  capabilities: Capabilities;
  formats: Formats;
  metadata_state: MetadataState;
  producer_detection: ProducerDetection;
}
export interface SourceFormat {
  pixel_format: PixelFormat;
  width: Width;
  height: Height;
  fps: Fps;
}

}
export type SourceList = SourceListContract.SourceList;

export namespace InspectRequestContract {
export type SourceId = string;

export interface InspectRequest {
  source_id: SourceId;
}

}
export type InspectRequest = InspectRequestContract.InspectRequest;

export namespace ControlBootstrapContract {
export type SchemaVersion = "obs-control-1";
export type CsrfToken = string;
export type RecordingNotice =
  "Recording is optional and off by default. Consent saves private processed 16x16 inputs, raw neural responses and flight replay locally. These inputs can contain sensitive content. Full-resolution source video is never saved.";

export interface ControlBootstrap {
  schema_version?: SchemaVersion;
  csrf_token: CsrfToken;
  recording_notice?: RecordingNotice;
}

}
export type ControlBootstrap = ControlBootstrapContract.ControlBootstrap;

export namespace SourcePreviewContract {
export type SchemaVersion = "obs-frame-1";
export type SourceId = string;
export type SessionId = string;
export type Generation = number;
export type Sequence = number;
export type EvidenceKind = "real" | "fixture";
export type Width = number;
export type Height = number;
export type PixelFormat = "RGB24";
export type ReceiptMonotonicMs = number;
export type SourceTimestampMs = number | null;
export type SourceSequence = number | null;
export type SourceClock = "unknown" | "producer" | "local_monotonic";
export type Width1 = number;
export type Height1 = number;
export type RgbBase64 = string;
/**
 * @minItems 256
 * @maxItems 256
 */
export type ObservationU8 = [
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number
];

export interface SourcePreview {
  frame: FrameIdentity;
  width: Width1;
  height: Height1;
  rgb_base64: RgbBase64;
  observation_u8: ObservationU8;
}
export interface FrameIdentity {
  schema_version: SchemaVersion;
  source_id: SourceId;
  session_id: SessionId;
  generation: Generation;
  sequence: Sequence;
  evidence_kind: EvidenceKind;
  width: Width;
  height: Height;
  pixel_format: PixelFormat;
  receipt_monotonic_ms: ReceiptMonotonicMs;
  source_timestamp_ms: SourceTimestampMs;
  source_sequence: SourceSequence;
  source_clock: SourceClock;
}

}
export type SourcePreview = SourcePreviewContract.SourcePreview;

export namespace ApiSnapshotContract {
export type SchemaVersion = "obs-api-snapshot-1";
export type EventSequence = number;
export type SentMonotonicMs = number;
export type SchemaVersion1 = "obs-session-status-1";
export type SessionId = string;
export type Generation = number;
export type EvidenceKind = "real" | "fixture";
export type State =
  "idle" | "previewing" | "starting" | "running" | "stopping" | "stopped" | "source_lost" | "failed" | "limit_reached";
export type Reason = string | null;
export type AttemptedCalls = number;
export type AcceptedFrames = number;
export type OverwrittenFrames = number;
export type ContentUnchangedMs = number;
export type ProducerHealth = "unknown" | "active" | "inactive";
export type LastFrameSequence = number | null;
export type LastResponseId = string | null;
export type SchemaVersion2 = "obs-frame-1";
export type SourceId = string;
export type SessionId1 = string;
export type Generation1 = number;
export type Sequence = number;
export type EvidenceKind1 = "real" | "fixture";
export type Width = number;
export type Height = number;
export type PixelFormat = "RGB24";
export type ReceiptMonotonicMs = number;
export type SourceTimestampMs = number | null;
export type SourceSequence = number | null;
export type SourceClock = "unknown" | "producer" | "local_monotonic";
export type SchemaVersion3 = "obs-neural-1";
export type ResponseId = string;
/**
 * @minItems 256
 * @maxItems 256
 */
export type ObservationU8 = [
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number
];
export type EncoderId = "obs-rgb-letterbox16-v1";
export type ModelId = string;
export type StepIndex = number;
export type CompletedMonotonicMs = number;
export type NeuralMs = 20;
export type NeuralStateMode = "windowed_reset";
export type SteerL = number;
export type SteerR = number;
export type FwdL = number;
export type FwdR = number;
export type Back = number;
export type Stop = number;
export type Click = number;
export type Dx = number;
export type Dy = number;
export type Click1 = boolean;
export type SchemaVersion4 = "obs-flight-1";
export type SessionId2 = string;
export type Generation2 = number;
export type EvidenceKind2 = "real" | "fixture";
export type Tick = number;
/**
 * @minItems 3
 * @maxItems 3
 */
export type Position = [number, number, number];
export type YawRad = number;
export type PitchRad = number;
export type SpeedUnitsS = number;
export type AppliedResponseId = string | null;
export type Neutral = boolean;
export type Kind = "session" | "preview";
export type LeaseRemainingMs = number;
export type SourceReceiptAgeMs = number | null;
export type ResponseAgeMs = number | null;
export type CompletedCalls = number;
export type RejectedResults = number;
export type ModelHz = number;
export type LastStepWallMs = number | null;
export type RecordingId = string | null;
export type RecordingState = "off" | "partial" | "aborted" | "complete";

export interface ApiSnapshot {
  schema_version?: SchemaVersion;
  event_sequence: EventSequence;
  sent_monotonic_ms: SentMonotonicMs;
  status: SessionStatus;
  latest_source_frame: FrameIdentity | null;
  neural_sample: NeuralSample | null;
  flight: FlightSnapshot | null;
  kind: Kind;
  lease_remaining_ms: LeaseRemainingMs;
  source_receipt_age_ms: SourceReceiptAgeMs;
  response_age_ms: ResponseAgeMs;
  last_inferred: NeuralSample | null;
  completed_calls: CompletedCalls;
  rejected_results: RejectedResults;
  model_hz: ModelHz;
  last_step_wall_ms: LastStepWallMs;
  recording_id: RecordingId;
  recording_state: RecordingState;
}
export interface SessionStatus {
  schema_version: SchemaVersion1;
  session_id: SessionId;
  generation: Generation;
  evidence_kind: EvidenceKind;
  state: State;
  reason: Reason;
  attempted_calls: AttemptedCalls;
  accepted_frames: AcceptedFrames;
  overwritten_frames: OverwrittenFrames;
  content_unchanged_ms: ContentUnchangedMs;
  producer_health: ProducerHealth;
  last_frame_sequence: LastFrameSequence;
  last_response_id: LastResponseId;
}
export interface FrameIdentity {
  schema_version: SchemaVersion2;
  source_id: SourceId;
  session_id: SessionId1;
  generation: Generation1;
  sequence: Sequence;
  evidence_kind: EvidenceKind1;
  width: Width;
  height: Height;
  pixel_format: PixelFormat;
  receipt_monotonic_ms: ReceiptMonotonicMs;
  source_timestamp_ms: SourceTimestampMs;
  source_sequence: SourceSequence;
  source_clock: SourceClock;
}
export interface NeuralSample {
  schema_version: SchemaVersion3;
  response_id: ResponseId;
  frame: FrameIdentity;
  observation_u8: ObservationU8;
  encoder_id: EncoderId;
  model_id: ModelId;
  step_index: StepIndex;
  completed_monotonic_ms: CompletedMonotonicMs;
  neural_ms: NeuralMs;
  neural_state_mode: NeuralStateMode;
  motor_rates_hz: MotorRates;
  raw_action: RawAction;
}
export interface MotorRates {
  steer_L: SteerL;
  steer_R: SteerR;
  fwd_L: FwdL;
  fwd_R: FwdR;
  back: Back;
  stop: Stop;
  click: Click;
}
export interface RawAction {
  dx: Dx;
  dy: Dy;
  click: Click1;
}
export interface FlightSnapshot {
  schema_version: SchemaVersion4;
  session_id: SessionId2;
  generation: Generation2;
  evidence_kind: EvidenceKind2;
  tick: Tick;
  position: Position;
  yaw_rad: YawRad;
  pitch_rad: PitchRad;
  speed_units_s: SpeedUnitsS;
  applied_response_id: AppliedResponseId;
  neutral: Neutral;
}

}
export type ApiSnapshot = ApiSnapshotContract.ApiSnapshot;

export namespace ServiceStatusContract {
export type SchemaVersion = "obs-service-status-1";
export type SchemaVersion1 = "obs-api-snapshot-1";
export type EventSequence = number;
export type SentMonotonicMs = number;
export type SchemaVersion2 = "obs-session-status-1";
export type SessionId = string;
export type Generation = number;
export type EvidenceKind = "real" | "fixture";
export type State =
  "idle" | "previewing" | "starting" | "running" | "stopping" | "stopped" | "source_lost" | "failed" | "limit_reached";
export type Reason = string | null;
export type AttemptedCalls = number;
export type AcceptedFrames = number;
export type OverwrittenFrames = number;
export type ContentUnchangedMs = number;
export type ProducerHealth = "unknown" | "active" | "inactive";
export type LastFrameSequence = number | null;
export type LastResponseId = string | null;
export type SchemaVersion3 = "obs-frame-1";
export type SourceId = string;
export type SessionId1 = string;
export type Generation1 = number;
export type Sequence = number;
export type EvidenceKind1 = "real" | "fixture";
export type Width = number;
export type Height = number;
export type PixelFormat = "RGB24";
export type ReceiptMonotonicMs = number;
export type SourceTimestampMs = number | null;
export type SourceSequence = number | null;
export type SourceClock = "unknown" | "producer" | "local_monotonic";
export type SchemaVersion4 = "obs-neural-1";
export type ResponseId = string;
/**
 * @minItems 256
 * @maxItems 256
 */
export type ObservationU8 = [
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number
];
export type EncoderId = "obs-rgb-letterbox16-v1";
export type ModelId = string;
export type StepIndex = number;
export type CompletedMonotonicMs = number;
export type NeuralMs = 20;
export type NeuralStateMode = "windowed_reset";
export type SteerL = number;
export type SteerR = number;
export type FwdL = number;
export type FwdR = number;
export type Back = number;
export type Stop = number;
export type Click = number;
export type Dx = number;
export type Dy = number;
export type Click1 = boolean;
export type SchemaVersion5 = "obs-flight-1";
export type SessionId2 = string;
export type Generation2 = number;
export type EvidenceKind2 = "real" | "fixture";
export type Tick = number;
/**
 * @minItems 3
 * @maxItems 3
 */
export type Position = [number, number, number];
export type YawRad = number;
export type PitchRad = number;
export type SpeedUnitsS = number;
export type AppliedResponseId = string | null;
export type Neutral = boolean;
export type Kind = "session" | "preview";
export type LeaseRemainingMs = number;
export type SourceReceiptAgeMs = number | null;
export type ResponseAgeMs = number | null;
export type CompletedCalls = number;
export type RejectedResults = number;
export type ModelHz = number;
export type LastStepWallMs = number | null;
export type RecordingId = string | null;
export type RecordingState = "off" | "partial" | "aborted" | "complete";

export interface ServiceStatus {
  schema_version?: SchemaVersion;
  current: ApiSnapshot | null;
}
export interface ApiSnapshot {
  schema_version?: SchemaVersion1;
  event_sequence: EventSequence;
  sent_monotonic_ms: SentMonotonicMs;
  status: SessionStatus;
  latest_source_frame: FrameIdentity | null;
  neural_sample: NeuralSample | null;
  flight: FlightSnapshot | null;
  kind: Kind;
  lease_remaining_ms: LeaseRemainingMs;
  source_receipt_age_ms: SourceReceiptAgeMs;
  response_age_ms: ResponseAgeMs;
  last_inferred: NeuralSample | null;
  completed_calls: CompletedCalls;
  rejected_results: RejectedResults;
  model_hz: ModelHz;
  last_step_wall_ms: LastStepWallMs;
  recording_id: RecordingId;
  recording_state: RecordingState;
}
export interface SessionStatus {
  schema_version: SchemaVersion2;
  session_id: SessionId;
  generation: Generation;
  evidence_kind: EvidenceKind;
  state: State;
  reason: Reason;
  attempted_calls: AttemptedCalls;
  accepted_frames: AcceptedFrames;
  overwritten_frames: OverwrittenFrames;
  content_unchanged_ms: ContentUnchangedMs;
  producer_health: ProducerHealth;
  last_frame_sequence: LastFrameSequence;
  last_response_id: LastResponseId;
}
export interface FrameIdentity {
  schema_version: SchemaVersion3;
  source_id: SourceId;
  session_id: SessionId1;
  generation: Generation1;
  sequence: Sequence;
  evidence_kind: EvidenceKind1;
  width: Width;
  height: Height;
  pixel_format: PixelFormat;
  receipt_monotonic_ms: ReceiptMonotonicMs;
  source_timestamp_ms: SourceTimestampMs;
  source_sequence: SourceSequence;
  source_clock: SourceClock;
}
export interface NeuralSample {
  schema_version: SchemaVersion4;
  response_id: ResponseId;
  frame: FrameIdentity;
  observation_u8: ObservationU8;
  encoder_id: EncoderId;
  model_id: ModelId;
  step_index: StepIndex;
  completed_monotonic_ms: CompletedMonotonicMs;
  neural_ms: NeuralMs;
  neural_state_mode: NeuralStateMode;
  motor_rates_hz: MotorRates;
  raw_action: RawAction;
}
export interface MotorRates {
  steer_L: SteerL;
  steer_R: SteerR;
  fwd_L: FwdL;
  fwd_R: FwdR;
  back: Back;
  stop: Stop;
  click: Click;
}
export interface RawAction {
  dx: Dx;
  dy: Dy;
  click: Click1;
}
export interface FlightSnapshot {
  schema_version: SchemaVersion5;
  session_id: SessionId2;
  generation: Generation2;
  evidence_kind: EvidenceKind2;
  tick: Tick;
  position: Position;
  yaw_rad: YawRad;
  pitch_rad: PitchRad;
  speed_units_s: SpeedUnitsS;
  applied_response_id: AppliedResponseId;
  neutral: Neutral;
}

}
export type ServiceStatus = ServiceStatusContract.ServiceStatus;

export namespace PreviewReplyContract {
export type SchemaVersion = "obs-source-preview-1";
export type SchemaVersion1 = "obs-session-status-1";
export type SessionId = string;
export type Generation = number;
export type EvidenceKind = "real" | "fixture";
export type State =
  "idle" | "previewing" | "starting" | "running" | "stopping" | "stopped" | "source_lost" | "failed" | "limit_reached";
export type Reason = string | null;
export type AttemptedCalls = number;
export type AcceptedFrames = number;
export type OverwrittenFrames = number;
export type ContentUnchangedMs = number;
export type ProducerHealth = "unknown" | "active" | "inactive";
export type LastFrameSequence = number | null;
export type LastResponseId = string | null;
export type SchemaVersion2 = "obs-frame-1";
export type SourceId = string;
export type SessionId1 = string;
export type Generation1 = number;
export type Sequence = number;
export type EvidenceKind1 = "real" | "fixture";
export type Width = number;
export type Height = number;
export type PixelFormat = "RGB24";
export type ReceiptMonotonicMs = number;
export type SourceTimestampMs = number | null;
export type SourceSequence = number | null;
export type SourceClock = "unknown" | "producer" | "local_monotonic";
export type Width1 = number;
export type Height1 = number;
export type RgbBase64 = string;
/**
 * @minItems 256
 * @maxItems 256
 */
export type ObservationU8 = [
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number
];

export interface PreviewReply {
  schema_version?: SchemaVersion;
  status: SessionStatus;
  latest: SourcePreview | null;
}
export interface SessionStatus {
  schema_version: SchemaVersion1;
  session_id: SessionId;
  generation: Generation;
  evidence_kind: EvidenceKind;
  state: State;
  reason: Reason;
  attempted_calls: AttemptedCalls;
  accepted_frames: AcceptedFrames;
  overwritten_frames: OverwrittenFrames;
  content_unchanged_ms: ContentUnchangedMs;
  producer_health: ProducerHealth;
  last_frame_sequence: LastFrameSequence;
  last_response_id: LastResponseId;
}
export interface SourcePreview {
  frame: FrameIdentity;
  width: Width1;
  height: Height1;
  rgb_base64: RgbBase64;
  observation_u8: ObservationU8;
}
export interface FrameIdentity {
  schema_version: SchemaVersion2;
  source_id: SourceId;
  session_id: SessionId1;
  generation: Generation1;
  sequence: Sequence;
  evidence_kind: EvidenceKind1;
  width: Width;
  height: Height;
  pixel_format: PixelFormat;
  receipt_monotonic_ms: ReceiptMonotonicMs;
  source_timestamp_ms: SourceTimestampMs;
  source_sequence: SourceSequence;
  source_clock: SourceClock;
}

}
export type PreviewReply = PreviewReplyContract.PreviewReply;

export namespace ReplayPayloadContract {
export type SchemaVersion = "obs-recorded-replay-1";
export type SchemaVersion1 = "obs-replay-1";
export type SessionId = string;
export type Generation = number;
export type EvidenceKind = "real" | "fixture";
export type State = "partial" | "aborted" | "complete";
export type SchemaVersion2 = "obs-session-config-1";
export type SourceId = string;
export type EvidenceKind1 = "real" | "fixture";
export type Seed = number;
export type Recording = boolean;
export type DurationSeconds = number;
export type MaxModelCalls = number;
export type SourceDeadlineMs = number;
export type StepDeadlineMs = number;
export type StartupDeadlineMs = number;
export type ResponseMaxAgeMs = number;
export type LeaseMs = number;
export type StopGraceMs = number;
export type RecordingMaxBytes = number;
export type FixedStepMs = 20;
export type SchemaVersion3 = "obs-encoder-1";
export type EncoderId = "obs-rgb-letterbox16-v1";
export type Size = 16;
export type Grayscale = "(77R+150G+29B+128)//256";
export type Resampler = "nearest-pixel-center";
export type PaddingU8 = 0;
export type Color = "full-range-rgb-bt601-conversion";
export type DecoderId = "motor-flight-v1";
export type NeuralStateMode = "windowed_reset";
export type LearningEnabled = false;
export type SchemaVersion4 = "obs-source-1";
export type SourceId1 = string;
export type EvidenceKind2 = "real" | "fixture";
export type Name = string;
export type Driver = string | null;
export type Backend = "ffmpeg-v4l2" | "synthetic";
export type Capabilities =
  | []
  | ["video_capture" | "streaming" | "readwrite"]
  | ["video_capture" | "streaming" | "readwrite", "video_capture" | "streaming" | "readwrite"]
  | [
      "video_capture" | "streaming" | "readwrite",
      "video_capture" | "streaming" | "readwrite",
      "video_capture" | "streaming" | "readwrite"
    ]
  | null;
export type Formats = SourceFormat[] | null;
export type PixelFormat = "RGB24" | "BGR24" | "YUYV" | "NV12" | "MJPEG";
export type Width = number;
export type Height = number;
export type Fps = number;
export type MetadataState = "available" | "partial" | "unavailable";
export type ProducerDetection = "unknown" | "driver" | "obs_readonly_monitor" | "synthetic";
export type SchemaVersion5 = "obs-flight-1";
export type SessionId1 = string;
export type Generation1 = number;
export type EvidenceKind3 = "real" | "fixture";
export type Tick = number;
/**
 * @minItems 3
 * @maxItems 3
 */
export type Position = [number, number, number];
export type YawRad = number;
export type PitchRad = number;
export type SpeedUnitsS = number;
export type AppliedResponseId = string | null;
export type Neutral = boolean;
export type SourceHead = string;
export type SourceTreeSha256 = string;
export type GraphSha256 = string;
export type AnnotationsSha256 = string;
export type CheckpointSha256 = string;
export type ModelSourceSha256 = string;
export type ModelConfigSha256 = string;
export type BackendVersion = string;
export type PythonVersion = string;
export type NumpyVersion = string;
export type ScipyVersion = string;
export type ModelId = string;
export type NeuralStateMode1 = "windowed_reset";
export type Gains = "all-one-float32";
export type LearningEnabled1 = false;
export type EventsSha256 = string;
export type EventCount = number;
export type EventsBytes = number;
export type EventsFile = "events.jsonl";
export type Kind = "input";
export type SchemaVersion6 = "obs-frame-1";
export type SourceId2 = string;
export type SessionId2 = string;
export type Generation2 = number;
export type Sequence = number;
export type EvidenceKind4 = "real" | "fixture";
export type Width1 = number;
export type Height1 = number;
export type PixelFormat1 = "RGB24";
export type ReceiptMonotonicMs = number;
export type SourceTimestampMs = number | null;
export type SourceSequence = number | null;
export type SourceClock = "unknown" | "producer" | "local_monotonic";
/**
 * @minItems 256
 * @maxItems 256
 */
export type ObservationU8 = [
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number
];
export type StepIndex = number;
export type EncoderId1 = "obs-rgb-letterbox16-v1";
/**
 * @maxItems 512
 */
export type Inputs = InputEvent[];
export type SchemaVersion7 = "obs-neural-1";
export type ResponseId = string;
/**
 * @minItems 256
 * @maxItems 256
 */
export type ObservationU81 = [
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number
];
export type EncoderId2 = "obs-rgb-letterbox16-v1";
export type ModelId1 = string;
export type StepIndex1 = number;
export type CompletedMonotonicMs = number;
export type NeuralMs = 20;
export type NeuralStateMode2 = "windowed_reset";
export type SteerL = number;
export type SteerR = number;
export type FwdL = number;
export type FwdR = number;
export type Back = number;
export type Stop = number;
export type Click = number;
export type Dx = number;
export type Dy = number;
export type Click1 = boolean;
/**
 * @maxItems 512
 */
export type Samples = NeuralSample[];
export type Kind1 = "result";
export type SessionId3 = string;
export type Generation3 = number;
export type StepIndex2 = number;
export type CompletedMonotonicMs1 = number;
export type SchemaVersion8 = "1";
export type Dx1 = number;
export type Dy1 = number;
export type Click2 = boolean;
export type ModelMode = "fixture" | "windowed_reset";
export type SchemaVersion9 = "1";
export type SampledNeurons = number;
export type SpikeCount = number;
export type NeuralMs1 = number;
export type SampledNeurons1 = number;
export type SpikeCount1 = number;
export type Firing = number;
export type SpikesPerSec = number;
export type MeanMv = number;
export type Visual = number;
export type Motor = number;
export type ModelFileReads = number;
/**
 * @maxItems 512
 */
export type Results = StepResult[];
export type SchemaVersion10 = "obs-flight-trace-1";
export type DecoderId1 = "motor-flight-v1";
export type PhysicsId = "flight-fixed20-v1";
/**
 * @minItems 3
 * @maxItems 3
 */
export type Velocity = [unknown, unknown, unknown];
export type YawRate = number;
export type OriginMs = number;
export type Tick1 = number;
export type SchemaVersion11 = "obs-controls-1";
export type DecoderId2 = "motor-flight-v1";
export type ResponseId1 = string;
export type SessionId4 = string;
export type Generation4 = number;
export type EvidenceKind5 = "real" | "fixture";
export type IssuedMonotonicMs = number;
export type ExpiresMonotonicMs = number;
export type YawRateRadS = number;
export type PitchTargetRad = number;
export type SpeedTargetUnitsS = number;
export type State1 =
  "idle" | "previewing" | "starting" | "running" | "stopping" | "stopped" | "source_lost" | "failed" | "limit_reached";
/**
 * @maxItems 512
 */
export type Events = ControlTick[];
export type Ticks = number;
export type TerminalTick = number | null;

export interface ReplayPayload {
  schema_version?: SchemaVersion;
  manifest: ReplayManifest;
  inputs: Inputs;
  samples: Samples;
  results: Results;
  trace: FlightTrace;
  final: FlightState;
}
export interface ReplayManifest {
  schema_version: SchemaVersion1;
  session_id: SessionId;
  generation: Generation;
  evidence_kind: EvidenceKind;
  state: State;
  config: SessionConfig;
  source: SourceCapability;
  initial_flight: FlightSnapshot;
  provenance: Provenance;
  events_sha256: EventsSha256;
  event_count: EventCount;
  events_bytes: EventsBytes;
  events_file: EventsFile;
}
export interface SessionConfig {
  schema_version?: SchemaVersion2;
  source_id: SourceId;
  evidence_kind: EvidenceKind1;
  seed: Seed;
  recording?: Recording;
  duration_seconds?: DurationSeconds;
  max_model_calls?: MaxModelCalls;
  source_deadline_ms?: SourceDeadlineMs;
  step_deadline_ms?: StepDeadlineMs;
  startup_deadline_ms?: StartupDeadlineMs;
  response_max_age_ms?: ResponseMaxAgeMs;
  lease_ms?: LeaseMs;
  stop_grace_ms?: StopGraceMs;
  recording_max_bytes?: RecordingMaxBytes;
  fixed_step_ms?: FixedStepMs;
  encoder?: EncoderConfig;
  decoder_id?: DecoderId;
  neural_state_mode?: NeuralStateMode;
  learning_enabled?: LearningEnabled;
}
export interface EncoderConfig {
  schema_version?: SchemaVersion3;
  encoder_id?: EncoderId;
  size?: Size;
  grayscale?: Grayscale;
  resampler?: Resampler;
  padding_u8?: PaddingU8;
  color?: Color;
}
export interface SourceCapability {
  schema_version: SchemaVersion4;
  source_id: SourceId1;
  evidence_kind: EvidenceKind2;
  name: Name;
  driver: Driver;
  backend: Backend;
  capabilities: Capabilities;
  formats: Formats;
  metadata_state: MetadataState;
  producer_detection: ProducerDetection;
}
export interface SourceFormat {
  pixel_format: PixelFormat;
  width: Width;
  height: Height;
  fps: Fps;
}
export interface FlightSnapshot {
  schema_version: SchemaVersion5;
  session_id: SessionId1;
  generation: Generation1;
  evidence_kind: EvidenceKind3;
  tick: Tick;
  position: Position;
  yaw_rad: YawRad;
  pitch_rad: PitchRad;
  speed_units_s: SpeedUnitsS;
  applied_response_id: AppliedResponseId;
  neutral: Neutral;
}
export interface Provenance {
  source_head: SourceHead;
  source_tree_sha256: SourceTreeSha256;
  graph_sha256: GraphSha256;
  annotations_sha256: AnnotationsSha256;
  checkpoint_sha256: CheckpointSha256;
  model_source_sha256: ModelSourceSha256;
  model_config_sha256: ModelConfigSha256;
  backend_version: BackendVersion;
  python_version: PythonVersion;
  numpy_version: NumpyVersion;
  scipy_version: ScipyVersion;
  model_id: ModelId;
  neural_state_mode: NeuralStateMode1;
  gains: Gains;
  learning_enabled: LearningEnabled1;
}
export interface InputEvent {
  kind?: Kind;
  frame: FrameIdentity;
  observation_u8: ObservationU8;
  step_index: StepIndex;
  encoder_id?: EncoderId1;
}
export interface FrameIdentity {
  schema_version: SchemaVersion6;
  source_id: SourceId2;
  session_id: SessionId2;
  generation: Generation2;
  sequence: Sequence;
  evidence_kind: EvidenceKind4;
  width: Width1;
  height: Height1;
  pixel_format: PixelFormat1;
  receipt_monotonic_ms: ReceiptMonotonicMs;
  source_timestamp_ms: SourceTimestampMs;
  source_sequence: SourceSequence;
  source_clock: SourceClock;
}
export interface NeuralSample {
  schema_version: SchemaVersion7;
  response_id: ResponseId;
  frame: FrameIdentity;
  observation_u8: ObservationU81;
  encoder_id: EncoderId2;
  model_id: ModelId1;
  step_index: StepIndex1;
  completed_monotonic_ms: CompletedMonotonicMs;
  neural_ms: NeuralMs;
  neural_state_mode: NeuralStateMode2;
  motor_rates_hz: MotorRates;
  raw_action: RawAction;
}
export interface MotorRates {
  steer_L: SteerL;
  steer_R: SteerR;
  fwd_L: FwdL;
  fwd_R: FwdR;
  back: Back;
  stop: Stop;
  click: Click;
}
export interface RawAction {
  dx: Dx;
  dy: Dy;
  click: Click1;
}
export interface StepResult {
  kind?: Kind1;
  session_id: SessionId3;
  generation: Generation3;
  step_index: StepIndex2;
  completed_monotonic_ms: CompletedMonotonicMs1;
  output: ControllerOutput;
  motor_rates_hz: MotorRates;
  raw_action: RawAction;
  statistics: Statistics;
  model_file_reads: ModelFileReads;
}
export interface ControllerOutput {
  schema_version: SchemaVersion8;
  dx: Dx1;
  dy: Dy1;
  click: Click2;
  model_mode: ModelMode;
  telemetry: NeuralTelemetry;
}
export interface NeuralTelemetry {
  schema_version: SchemaVersion9;
  sampled_neurons: SampledNeurons;
  spike_count: SpikeCount;
  neural_ms: NeuralMs1;
}
export interface Statistics {
  sampled_neurons: SampledNeurons1;
  spike_count: SpikeCount1;
  firing: Firing;
  spikes_per_sec: SpikesPerSec;
  mean_mv: MeanMv;
  visual: Visual;
  motor: Motor;
}
/**
 * Bounded in-memory state/control record, with an immediate terminal overlay.
 */
export interface FlightTrace {
  schema_version?: SchemaVersion10;
  decoder_id?: DecoderId1;
  initial: FlightState;
  origin_ms: OriginMs;
  events: Events;
  ticks: Ticks;
  terminal_tick: TerminalTick;
}
export interface FlightState {
  physics_id?: PhysicsId;
  snapshot: FlightSnapshot;
  velocity?: Velocity;
  yaw_rate?: YawRate;
}
/**
 * Control selected for the interval ending at tick; never a pixel record.
 */
export interface ControlTick {
  tick: Tick1;
  controls: FlightControls | null;
  state?: State1;
}
/**
 * Decoder output only; source pixels and world targets are excluded.
 */
export interface FlightControls {
  schema_version: SchemaVersion11;
  decoder_id: DecoderId2;
  response_id: ResponseId1;
  session_id: SessionId4;
  generation: Generation4;
  evidence_kind: EvidenceKind5;
  issued_monotonic_ms: IssuedMonotonicMs;
  expires_monotonic_ms: ExpiresMonotonicMs;
  yaw_rate_rad_s: YawRateRadS;
  pitch_target_rad: PitchTargetRad;
  speed_target_units_s: SpeedTargetUnitsS;
}

}
export type ReplayPayload = ReplayPayloadContract.ReplayPayload;

export namespace ReplayListContract {
export type SchemaVersion = "obs-replay-list-1";
export type RecordingId = string;
export type SchemaVersion1 = "obs-replay-1";
export type SessionId = string;
export type Generation = number;
export type EvidenceKind = "real" | "fixture";
export type State = "partial" | "aborted" | "complete";
export type SchemaVersion2 = "obs-session-config-1";
export type SourceId = string;
export type EvidenceKind1 = "real" | "fixture";
export type Seed = number;
export type Recording = boolean;
export type DurationSeconds = number;
export type MaxModelCalls = number;
export type SourceDeadlineMs = number;
export type StepDeadlineMs = number;
export type StartupDeadlineMs = number;
export type ResponseMaxAgeMs = number;
export type LeaseMs = number;
export type StopGraceMs = number;
export type RecordingMaxBytes = number;
export type FixedStepMs = 20;
export type SchemaVersion3 = "obs-encoder-1";
export type EncoderId = "obs-rgb-letterbox16-v1";
export type Size = 16;
export type Grayscale = "(77R+150G+29B+128)//256";
export type Resampler = "nearest-pixel-center";
export type PaddingU8 = 0;
export type Color = "full-range-rgb-bt601-conversion";
export type DecoderId = "motor-flight-v1";
export type NeuralStateMode = "windowed_reset";
export type LearningEnabled = false;
export type SchemaVersion4 = "obs-source-1";
export type SourceId1 = string;
export type EvidenceKind2 = "real" | "fixture";
export type Name = string;
export type Driver = string | null;
export type Backend = "ffmpeg-v4l2" | "synthetic";
export type Capabilities =
  | []
  | ["video_capture" | "streaming" | "readwrite"]
  | ["video_capture" | "streaming" | "readwrite", "video_capture" | "streaming" | "readwrite"]
  | [
      "video_capture" | "streaming" | "readwrite",
      "video_capture" | "streaming" | "readwrite",
      "video_capture" | "streaming" | "readwrite"
    ]
  | null;
export type Formats = SourceFormat[] | null;
export type PixelFormat = "RGB24" | "BGR24" | "YUYV" | "NV12" | "MJPEG";
export type Width = number;
export type Height = number;
export type Fps = number;
export type MetadataState = "available" | "partial" | "unavailable";
export type ProducerDetection = "unknown" | "driver" | "obs_readonly_monitor" | "synthetic";
export type SchemaVersion5 = "obs-flight-1";
export type SessionId1 = string;
export type Generation1 = number;
export type EvidenceKind3 = "real" | "fixture";
export type Tick = number;
/**
 * @minItems 3
 * @maxItems 3
 */
export type Position = [number, number, number];
export type YawRad = number;
export type PitchRad = number;
export type SpeedUnitsS = number;
export type AppliedResponseId = string | null;
export type Neutral = boolean;
export type SourceHead = string;
export type SourceTreeSha256 = string;
export type GraphSha256 = string;
export type AnnotationsSha256 = string;
export type CheckpointSha256 = string;
export type ModelSourceSha256 = string;
export type ModelConfigSha256 = string;
export type BackendVersion = string;
export type PythonVersion = string;
export type NumpyVersion = string;
export type ScipyVersion = string;
export type ModelId = string;
export type NeuralStateMode1 = "windowed_reset";
export type Gains = "all-one-float32";
export type LearningEnabled1 = false;
export type EventsSha256 = string;
export type EventCount = number;
export type EventsBytes = number;
export type EventsFile = "events.jsonl";
export type State1 = ("partial" | "aborted") | null;
export type Error = "Recording unavailable or corrupted." | null;
/**
 * @maxItems 128
 */
export type Recordings = ReplayListEntry[];

export interface ReplayList {
  schema_version?: SchemaVersion;
  recordings: Recordings;
}
export interface ReplayListEntry {
  recording_id: RecordingId;
  manifest?: ReplayManifest | null;
  state?: State1;
  error?: Error;
}
export interface ReplayManifest {
  schema_version: SchemaVersion1;
  session_id: SessionId;
  generation: Generation;
  evidence_kind: EvidenceKind;
  state: State;
  config: SessionConfig;
  source: SourceCapability;
  initial_flight: FlightSnapshot;
  provenance: Provenance;
  events_sha256: EventsSha256;
  event_count: EventCount;
  events_bytes: EventsBytes;
  events_file: EventsFile;
}
export interface SessionConfig {
  schema_version?: SchemaVersion2;
  source_id: SourceId;
  evidence_kind: EvidenceKind1;
  seed: Seed;
  recording?: Recording;
  duration_seconds?: DurationSeconds;
  max_model_calls?: MaxModelCalls;
  source_deadline_ms?: SourceDeadlineMs;
  step_deadline_ms?: StepDeadlineMs;
  startup_deadline_ms?: StartupDeadlineMs;
  response_max_age_ms?: ResponseMaxAgeMs;
  lease_ms?: LeaseMs;
  stop_grace_ms?: StopGraceMs;
  recording_max_bytes?: RecordingMaxBytes;
  fixed_step_ms?: FixedStepMs;
  encoder?: EncoderConfig;
  decoder_id?: DecoderId;
  neural_state_mode?: NeuralStateMode;
  learning_enabled?: LearningEnabled;
}
export interface EncoderConfig {
  schema_version?: SchemaVersion3;
  encoder_id?: EncoderId;
  size?: Size;
  grayscale?: Grayscale;
  resampler?: Resampler;
  padding_u8?: PaddingU8;
  color?: Color;
}
export interface SourceCapability {
  schema_version: SchemaVersion4;
  source_id: SourceId1;
  evidence_kind: EvidenceKind2;
  name: Name;
  driver: Driver;
  backend: Backend;
  capabilities: Capabilities;
  formats: Formats;
  metadata_state: MetadataState;
  producer_detection: ProducerDetection;
}
export interface SourceFormat {
  pixel_format: PixelFormat;
  width: Width;
  height: Height;
  fps: Fps;
}
export interface FlightSnapshot {
  schema_version: SchemaVersion5;
  session_id: SessionId1;
  generation: Generation1;
  evidence_kind: EvidenceKind3;
  tick: Tick;
  position: Position;
  yaw_rad: YawRad;
  pitch_rad: PitchRad;
  speed_units_s: SpeedUnitsS;
  applied_response_id: AppliedResponseId;
  neutral: Neutral;
}
export interface Provenance {
  source_head: SourceHead;
  source_tree_sha256: SourceTreeSha256;
  graph_sha256: GraphSha256;
  annotations_sha256: AnnotationsSha256;
  checkpoint_sha256: CheckpointSha256;
  model_source_sha256: ModelSourceSha256;
  model_config_sha256: ModelConfigSha256;
  backend_version: BackendVersion;
  python_version: PythonVersion;
  numpy_version: NumpyVersion;
  scipy_version: ScipyVersion;
  model_id: ModelId;
  neural_state_mode: NeuralStateMode1;
  gains: Gains;
  learning_enabled: LearningEnabled1;
}

}
export type ReplayList = ReplayListContract.ReplayList;

export namespace FlightStateContract {
export type PhysicsId = "flight-fixed20-v1";
export type SchemaVersion = "obs-flight-1";
export type SessionId = string;
export type Generation = number;
export type EvidenceKind = "real" | "fixture";
export type Tick = number;
/**
 * @minItems 3
 * @maxItems 3
 */
export type Position = [number, number, number];
export type YawRad = number;
export type PitchRad = number;
export type SpeedUnitsS = number;
export type AppliedResponseId = string | null;
export type Neutral = boolean;
/**
 * @minItems 3
 * @maxItems 3
 */
export type Velocity = [unknown, unknown, unknown];
export type YawRate = number;

export interface FlightState {
  physics_id?: PhysicsId;
  snapshot: FlightSnapshot;
  velocity?: Velocity;
  yaw_rate?: YawRate;
}
export interface FlightSnapshot {
  schema_version: SchemaVersion;
  session_id: SessionId;
  generation: Generation;
  evidence_kind: EvidenceKind;
  tick: Tick;
  position: Position;
  yaw_rad: YawRad;
  pitch_rad: PitchRad;
  speed_units_s: SpeedUnitsS;
  applied_response_id: AppliedResponseId;
  neutral: Neutral;
}

}
export type FlightState = FlightStateContract.FlightState;
