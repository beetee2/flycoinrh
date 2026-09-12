// Generated from flytrap/contracts.py JSON Schemas. Do not edit.
export namespace BenchmarkReportContract {
export type CheckpointSha256 = string;
export type ClaimStatus = "SUPPORTED" | "UNSUPPORTED" | "INCONCLUSIVE" | "NOT_RUN";
/**
 * @minItems 1
 * @maxItems 1024
 */
export type Cohorts = [string, ...string[]];
/**
 * @minItems 1
 * @maxItems 4096
 */
export type Layouts = [string, ...string[]];
/**
 * @minItems 1
 * @maxItems 32
 */
export type Limitations = [string, ...string[]];
export type InfrastructureFailures = number;
export type MeanStepsAllEpisodes = number;
export type ScheduledEpisodes = number;
export type SchemaVersion = "1";
export type SuccessFraction = number;
export type TimeoutFraction = number;
export type TotalWallMs = number;
export type WrongPadFraction = number;
export type ModelSha256 = string;
export type PreregistrationSha256 = string;
export type ReportId = string;
export type SchemaVersion1 = "1";
/**
 * @minItems 1
 * @maxItems 4096
 */
export type Seeds = [number, ...number[]];
export type SourceTreeSha256 = string;
export type ConfidenceLevel = 0.95;
export type Lower = number;
export type Method = "paired_layout_bootstrap" | "not_estimated";
export type SchemaVersion2 = "1";
export type Upper = number;

export interface BenchmarkReport {
  checkpoint_sha256: CheckpointSha256;
  claim_status: ClaimStatus;
  cohorts: Cohorts;
  layouts: Layouts;
  limitations: Limitations;
  metrics: BenchmarkMetrics;
  model_sha256: ModelSha256;
  preregistration_sha256: PreregistrationSha256;
  report_id: ReportId;
  schema_version: SchemaVersion1;
  seeds: Seeds;
  source_tree_sha256: SourceTreeSha256;
  uncertainty: Uncertainty;
}
export interface BenchmarkMetrics {
  infrastructure_failures: InfrastructureFailures;
  mean_steps_all_episodes: MeanStepsAllEpisodes;
  scheduled_episodes: ScheduledEpisodes;
  schema_version: SchemaVersion;
  success_fraction: SuccessFraction;
  timeout_fraction: TimeoutFraction;
  total_wall_ms: TotalWallMs;
  wrong_pad_fraction: WrongPadFraction;
}
export interface Uncertainty {
  confidence_level: ConfidenceLevel;
  lower: Lower;
  method: Method;
  schema_version: SchemaVersion2;
  upper: Upper;
}

}
export type BenchmarkReport = BenchmarkReportContract.BenchmarkReport;

export namespace CapabilitiesContract {
export type Admission = "unavailable" | "closed" | "open";
/**
 * @maxItems 32
 */
export type ApprovedCheckpointIds = string[];
/**
 * @maxItems 32
 */
export type ApprovedComparisonIds = string[];
export type Fixture = boolean;
export type LearningClaimStatus = "SUPPORTED" | "UNSUPPORTED" | "INCONCLUSIVE" | "NOT_RUN";
export type RealModelAvailable = boolean;
export type SchemaVersion = "1";

export interface Capabilities {
  admission: Admission;
  approved_checkpoint_ids: ApprovedCheckpointIds;
  approved_comparison_ids: ApprovedComparisonIds;
  fixture: Fixture;
  learning_claim_status: LearningClaimStatus;
  real_model_available: RealModelAvailable;
  schema_version: SchemaVersion;
}

}
export type Capabilities = CapabilitiesContract.Capabilities;

export namespace ChallengeSpecContract {
export type ContentSha256 = string;
export type DestinationSide = "left" | "right";
/**
 * @maxItems 3
 */
export type Distractions =
  | []
  | ["top" | "middle" | "bottom"]
  | ["top" | "middle" | "bottom", "top" | "middle" | "bottom"]
  | ["top" | "middle" | "bottom", "top" | "middle" | "bottom", "top" | "middle" | "bottom"];
export type LeftTexture = "stripes" | "checkerboard";
export type PresetVersion = "two_choice_v1";
export type RendererVersion = "grayscale_v1";
export type RightTexture = "stripes" | "checkerboard";
export type SchemaVersion = "1";

export interface ChallengeSpec {
  content_sha256: ContentSha256;
  destination_side: DestinationSide;
  distractions: Distractions;
  left_texture: LeftTexture;
  preset_version: PresetVersion;
  renderer_version: RendererVersion;
  right_texture: RightTexture;
  schema_version: SchemaVersion;
}

}
export type ChallengeSpec = ChallengeSpecContract.ChallengeSpec;

export namespace CheckpointRefContract {
export type CheckpointId = string;
export type GraphSha256 = string;
export type ModelMode = "fixture" | "windowed_reset";
export type SchemaVersion = "1";
export type Sha256 = string;

export interface CheckpointRef {
  checkpoint_id: CheckpointId;
  graph_sha256: GraphSha256;
  model_mode: ModelMode;
  schema_version: SchemaVersion;
  sha256: Sha256;
}

}
export type CheckpointRef = CheckpointRefContract.CheckpointRef;

export namespace ControllerOutputContract {
export type Click = boolean;
export type Dx = number;
export type Dy = number;
export type ModelMode = "fixture" | "windowed_reset";
export type SchemaVersion = "1";
export type NeuralMs = number;
export type SampledNeurons = number;
export type SchemaVersion1 = "1";
export type SpikeCount = number;

export interface ControllerOutput {
  click: Click;
  dx: Dx;
  dy: Dy;
  model_mode: ModelMode;
  schema_version: SchemaVersion;
  telemetry: NeuralTelemetry;
}
export interface NeuralTelemetry {
  neural_ms: NeuralMs;
  sampled_neurons: SampledNeurons;
  schema_version: SchemaVersion1;
  spike_count: SpikeCount;
}

}
export type ControllerOutput = ControllerOutputContract.ControllerOutput;

export namespace ErrorResponseContract {
export type Code =
  | "invalid_request"
  | "unavailable"
  | "queue_full"
  | "quota_exceeded"
  | "idempotency_conflict"
  | "not_found"
  | "internal_error"
  | "resource_deadline";
export type Message = string;
export type Retryable = boolean;
export type SchemaVersion = "1";

export interface ErrorResponse {
  code: Code;
  message: Message;
  retryable: Retryable;
  schema_version: SchemaVersion;
}

}
export type ErrorResponse = ErrorResponseContract.ErrorResponse;

export namespace FrameEventContract {
export type Click = boolean;
export type Dx = number;
export type Dy = number;
export type ModelMode = "fixture" | "windowed_reset";
export type SchemaVersion = "1";
export type NeuralMs = number;
export type SampledNeurons = number;
export type SchemaVersion1 = "1";
export type SpikeCount = number;
export type Attempt = number;
export type EventSequence = number;
export type FrameSha256 = string;
export type ObservationSha256 = string;
export type SchemaVersion2 = "1";
export type X = number;
export type Y = number;
export type RunId = string;
export type SchemaVersion3 = "1";
export type Tick = number;
export type TimestampMs = number;

export interface FrameEvent {
  action: ControllerOutput;
  attempt: Attempt;
  event_sequence: EventSequence;
  frame_sha256: FrameSha256;
  observation_sha256: ObservationSha256;
  position: Position;
  run_id: RunId;
  schema_version: SchemaVersion3;
  tick: Tick;
  timestamp_ms: TimestampMs;
}
export interface ControllerOutput {
  click: Click;
  dx: Dx;
  dy: Dy;
  model_mode: ModelMode;
  schema_version: SchemaVersion;
  telemetry: NeuralTelemetry;
}
export interface NeuralTelemetry {
  neural_ms: NeuralMs;
  sampled_neurons: SampledNeurons;
  schema_version: SchemaVersion1;
  spike_count: SpikeCount;
}
export interface Position {
  schema_version: SchemaVersion2;
  x: X;
  y: Y;
}

}
export type FrameEvent = FrameEventContract.FrameEvent;

export namespace ObservationContract {
/**
 * @minItems 256
 * @maxItems 256
 */
export type Pixels = [
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
  number,
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
export type SchemaVersion = "1";

export interface Observation {
  pixels: Pixels;
  schema_version: SchemaVersion;
}

}
export type Observation = ObservationContract.Observation;

export namespace ReplayManifestContract {
export type MovementPerTick = number;
export type SchemaVersion = "1";
export type Version = "bounded_xy_v1";
export type ArenaVersion = "two_choice_v1";
export type ArtifactId = string;
export type Bytes = number;
export type SchemaVersion1 = "1";
export type Sha256 = string;
/**
 * @maxItems 128
 */
export type Artifacts = ArtifactRef[];
export type BenchmarkReportId = string | null;
export type CalibrationId = string;
export type ConfigSha256 = string;
export type Gain = number;
export type SchemaVersion2 = "1";
export type ChallengeId = string;
export type ChallengeSha256 = string;
export type CheckpointId = string;
export type GraphSha256 = string;
export type ModelMode = "fixture" | "windowed_reset";
export type SchemaVersion3 = "1";
export type Sha2561 = string;
export type ArtifactId1 = string;
export type Bytes1 = number;
export type EventCount = number;
export type FirstTick = number;
export type SchemaVersion4 = "1";
export type Sequence = number;
export type Sha2562 = string;
/**
 * @maxItems 4096
 */
export type Chunks = TraceChunk[];
export type ClaimStatus = "SUPPORTED" | "UNSUPPORTED" | "INCONCLUSIVE" | "NOT_RUN";
export type Completion = "complete" | "incomplete";
/**
 * @minItems 1
 * @maxItems 32
 */
export type DataSha256 = [string, ...string[]];
export type GraphSha2561 = string;
export type OrderedBodyMappingSha256 = string;
export type OrderedSynapseMappingSha256 = string;
export type SchemaVersion5 = "1";
export type Node = string;
export type NodeLockSha256 = string;
export type Platform = string;
export type Python = string;
export type PythonLockSha256 = string;
export type SchemaVersion6 = "1";
export type Sqlite = string;
export type EnvironmentTicks = number;
export type FinalResult = ("success" | "wrong_pad" | "trial_timeout" | "infrastructure_failure") | null;
export type Fixture = boolean;
export type SchemaVersion7 = "1";
export type X = number;
export type Y = number;
export type NeuralStateMode = "fixture" | "windowed_reset";
export type RandomStreamVersion = "seed32_v1";
export type RendererVersion = "grayscale_v1";
export type RewardVersion = "destination_v1";
export type RunId = string;
export type RunSeed = number;
export type SchemaVersion8 = "1";
export type SimulatedMs = number;
export type SourceCommit = string;
export type SourceTreeSha256 = string;
export type TraceSha256 = string;
export type UpstreamRevision = string;
export type WallMs = number;

export interface ReplayManifest {
  action_mapping: ActionMapping;
  arena_version: ArenaVersion;
  artifacts: Artifacts;
  benchmark_report_id: BenchmarkReportId;
  calibration: Calibration;
  challenge_id: ChallengeId;
  challenge_sha256: ChallengeSha256;
  checkpoint: CheckpointRef;
  chunks: Chunks;
  claim_status: ClaimStatus;
  completion: Completion;
  data: DataProvenance;
  environment: DependencyVersions;
  environment_ticks: EnvironmentTicks;
  final_result: FinalResult;
  fixture: Fixture;
  initial_state: Position;
  neural_state_mode: NeuralStateMode;
  random_stream_version: RandomStreamVersion;
  renderer_version: RendererVersion;
  reward_version: RewardVersion;
  run_id: RunId;
  run_seed: RunSeed;
  schema_version: SchemaVersion8;
  simulated_ms: SimulatedMs;
  source_commit: SourceCommit;
  source_tree_sha256: SourceTreeSha256;
  trace_sha256: TraceSha256;
  upstream_revision: UpstreamRevision;
  wall_ms: WallMs;
}
export interface ActionMapping {
  movement_per_tick: MovementPerTick;
  schema_version: SchemaVersion;
  version: Version;
}
export interface ArtifactRef {
  artifact_id: ArtifactId;
  bytes: Bytes;
  schema_version: SchemaVersion1;
  sha256: Sha256;
}
export interface Calibration {
  calibration_id: CalibrationId;
  config_sha256: ConfigSha256;
  gain: Gain;
  schema_version: SchemaVersion2;
}
export interface CheckpointRef {
  checkpoint_id: CheckpointId;
  graph_sha256: GraphSha256;
  model_mode: ModelMode;
  schema_version: SchemaVersion3;
  sha256: Sha2561;
}
export interface TraceChunk {
  artifact_id: ArtifactId1;
  bytes: Bytes1;
  event_count: EventCount;
  first_tick: FirstTick;
  schema_version: SchemaVersion4;
  sequence: Sequence;
  sha256: Sha2562;
}
export interface DataProvenance {
  data_sha256: DataSha256;
  graph_sha256: GraphSha2561;
  ordered_body_mapping_sha256: OrderedBodyMappingSha256;
  ordered_synapse_mapping_sha256: OrderedSynapseMappingSha256;
  schema_version: SchemaVersion5;
}
export interface DependencyVersions {
  node: Node;
  node_lock_sha256: NodeLockSha256;
  platform: Platform;
  python: Python;
  python_lock_sha256: PythonLockSha256;
  schema_version: SchemaVersion6;
  sqlite: Sqlite;
}
export interface Position {
  schema_version: SchemaVersion7;
  x: X;
  y: Y;
}

}
export type ReplayManifest = ReplayManifestContract.ReplayManifest;

export namespace RunRecordContract {
export type Attempt = number;
export type ChallengeId = string;
export type ChallengeSha256 = string;
export type CheckpointId = string;
export type GraphSha256 = string;
export type ModelMode = "fixture" | "windowed_reset";
export type SchemaVersion = "1";
export type Sha256 = string;
export type ConfigSha256 = string;
export type ControllerId = "fixture_v1" | "fly_v1";
export type CreatedAtMs = number;
export type ErrorCode =
  | (
      | "invalid_request"
      | "unavailable"
      | "queue_full"
      | "quota_exceeded"
      | "idempotency_conflict"
      | "not_found"
      | "internal_error"
      | "resource_deadline"
    )
  | null;
export type FinishedAtMs = number | null;
export type RunId = string;
export type RunSeed = number;
export type SchemaVersion1 = "1";
export type StartedAtMs = number | null;
export type State = "queued" | "running" | "completed" | "failed" | "timed_out";

export interface RunRecord {
  attempt: Attempt;
  challenge_id: ChallengeId;
  challenge_sha256: ChallengeSha256;
  checkpoint: CheckpointRef;
  config_sha256: ConfigSha256;
  controller_id: ControllerId;
  created_at_ms: CreatedAtMs;
  error_code: ErrorCode;
  finished_at_ms: FinishedAtMs;
  run_id: RunId;
  run_seed: RunSeed;
  schema_version: SchemaVersion1;
  started_at_ms: StartedAtMs;
  state: State;
}
export interface CheckpointRef {
  checkpoint_id: CheckpointId;
  graph_sha256: GraphSha256;
  model_mode: ModelMode;
  schema_version: SchemaVersion;
  sha256: Sha256;
}

}
export type RunRecord = RunRecordContract.RunRecord;

export namespace RunRequestContract {
export type ChallengeId = string;
export type CheckpointId = string;
export type ControllerId = "fixture_v1" | "fly_v1";
export type SchemaVersion = "1";

export interface RunRequest {
  challenge_id: ChallengeId;
  checkpoint_id: CheckpointId;
  controller_id: ControllerId;
  schema_version: SchemaVersion;
}

}
export type RunRequest = RunRequestContract.RunRequest;
