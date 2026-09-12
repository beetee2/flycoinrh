"""Version 1 wire contracts. JSON Schema is exported from these models only.

Bounds are represented in JSON Schema so Python and browser validation agree.
The controller input deliberately exposes only a fixed grayscale raster.
"""

import hashlib
import json
import math
from types import UnionType
from typing import Annotated, Literal, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator


def _integral_number(value: object) -> object:
    # JSON Schema integers include 1.0 and 1e0. Strings/bools stay strict errors.
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    return value


def _normalize_integers(value: object, annotation: object) -> object:
    if annotation is int:
        return _integral_number(value)
    origin = get_origin(annotation)
    arguments = get_args(annotation)
    if origin is Annotated:
        return _normalize_integers(value, arguments[0])
    if origin is list and isinstance(value, list):
        return [_normalize_integers(item, arguments[0]) for item in value]
    if origin is UnionType and value is not None:
        for argument in arguments:
            if argument is not type(None):
                value = _normalize_integers(value, argument)
    return value


JsonInteger = int
SafeId = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$(?![\s\S])", max_length=64)]
Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$", min_length=64, max_length=64)]
GitRevision = Annotated[str, Field(pattern=r"^[0-9a-f]{40}$", min_length=40, max_length=40)]
Seed = Annotated[JsonInteger, Field(ge=0, le=4294967295)]
Counter = Annotated[JsonInteger, Field(ge=0, le=2147483647)]
TimestampMs = Annotated[JsonInteger, Field(ge=0, le=9007199254740991)]
UnitFloat = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
ActionFloat = Annotated[float, Field(ge=-1, le=1, allow_inf_nan=False)]
DurationMs = Annotated[float, Field(ge=0, le=1_000_000_000, allow_inf_nan=False)]
Version = Annotated[str, Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._+-]{0,63}$(?![\s\S])", max_length=64)]
RunState = Literal["queued", "running", "completed", "failed", "timed_out"]
ClaimStatus = Literal["SUPPORTED", "UNSUPPORTED", "INCONCLUSIVE", "NOT_RUN"]
ErrorCode = Literal[
    "invalid_request", "unavailable", "queue_full", "quota_exceeded",
    "idempotency_conflict", "not_found", "internal_error", "resource_deadline",
]
ModelMode = Literal["fixture", "windowed_reset"]
Result = Literal["success", "wrong_pad", "trial_timeout", "infrastructure_failure"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False, regex_engine="python-re")
    schema_version: Literal["1"]

    @field_validator("*", mode="before")
    @classmethod
    def normalize_json_integers(cls, value: object, info: ValidationInfo) -> object:
        return _normalize_integers(value, cls.model_fields[info.field_name].annotation)


class ChallengeSpec(Contract):
    preset_version: Literal["two_choice_v1"]
    renderer_version: Literal["grayscale_v1"]
    destination_side: Literal["left", "right"]
    left_texture: Literal["stripes", "checkerboard"]
    right_texture: Literal["stripes", "checkerboard"]
    distractions: Annotated[list[Literal["top", "middle", "bottom"]], Field(max_length=3)]
    content_sha256: Sha256


class RunRequest(Contract):
    challenge_id: SafeId
    controller_id: Literal["fixture_v1", "fly_v1"]
    checkpoint_id: SafeId
    # No caller seed. The server draws one unsigned 32-bit seed per admission.


class CheckpointRef(Contract):
    checkpoint_id: SafeId
    sha256: Sha256
    graph_sha256: Sha256
    model_mode: ModelMode


class RunRecord(Contract):
    run_id: SafeId
    challenge_id: SafeId
    challenge_sha256: Sha256
    run_seed: Seed
    config_sha256: Sha256
    controller_id: Literal["fixture_v1", "fly_v1"]
    checkpoint: CheckpointRef
    state: RunState
    attempt: Annotated[JsonInteger, Field(ge=0, le=16)]
    created_at_ms: TimestampMs
    started_at_ms: TimestampMs | None
    finished_at_ms: TimestampMs | None
    error_code: ErrorCode | None


class Observation(Contract):
    # 16 by 16, row-major, normalized grayscale. No world/task metadata.
    pixels: Annotated[list[UnitFloat], Field(min_length=256, max_length=256)]


class NeuralTelemetry(Contract):
    sampled_neurons: Annotated[JsonInteger, Field(ge=0, le=1_000_000)]
    spike_count: Annotated[JsonInteger, Field(ge=0, le=100_000_000)]
    neural_ms: Annotated[float, Field(ge=0, le=1_000_000, allow_inf_nan=False)]


class ControllerOutput(Contract):
    dx: ActionFloat
    dy: ActionFloat
    click: bool
    model_mode: ModelMode
    telemetry: NeuralTelemetry


class Position(Contract):
    x: Annotated[float, Field(ge=0, le=4096, allow_inf_nan=False)]
    y: Annotated[float, Field(ge=0, le=4096, allow_inf_nan=False)]


class FrameEvent(Contract):
    run_id: SafeId
    attempt: Annotated[JsonInteger, Field(ge=1, le=16)]
    tick: Counter
    event_sequence: Counter
    timestamp_ms: TimestampMs
    action: ControllerOutput
    position: Position
    frame_sha256: Sha256
    observation_sha256: Sha256


class DependencyVersions(Contract):
    python: Version
    node: Version
    sqlite: Version
    python_lock_sha256: Sha256
    node_lock_sha256: Sha256
    platform: Version


class DataProvenance(Contract):
    graph_sha256: Sha256
    data_sha256: Annotated[list[Sha256], Field(min_length=1, max_length=32)]
    ordered_body_mapping_sha256: Sha256
    ordered_synapse_mapping_sha256: Sha256


class Calibration(Contract):
    calibration_id: SafeId
    gain: Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]
    config_sha256: Sha256


class ActionMapping(Contract):
    version: Literal["bounded_xy_v1"]
    movement_per_tick: Annotated[float, Field(gt=0, le=64, allow_inf_nan=False)]


class ArtifactRef(Contract):
    artifact_id: SafeId
    sha256: Sha256
    bytes: Annotated[JsonInteger, Field(ge=0, le=1_073_741_824)]


class TraceChunk(ArtifactRef):
    sequence: Counter
    first_tick: Counter
    event_count: Annotated[JsonInteger, Field(ge=1, le=4096)]


class ReplayManifest(Contract):
    run_id: SafeId
    challenge_id: SafeId
    challenge_sha256: Sha256
    fixture: bool
    source_commit: GitRevision
    source_tree_sha256: Sha256
    upstream_revision: GitRevision
    environment: DependencyVersions
    data: DataProvenance
    checkpoint: CheckpointRef
    calibration: Calibration
    neural_state_mode: ModelMode
    run_seed: Seed
    random_stream_version: Literal["seed32_v1"]
    arena_version: Literal["two_choice_v1"]
    renderer_version: Literal["grayscale_v1"]
    reward_version: Literal["destination_v1"]
    action_mapping: ActionMapping
    initial_state: Position
    # Ordered chunks contain the complete action log and observation hashes.
    chunks: Annotated[list[TraceChunk], Field(max_length=4096)]
    trace_sha256: Sha256
    artifacts: Annotated[list[ArtifactRef], Field(max_length=128)]
    completion: Literal["complete", "incomplete"]
    final_result: Result | None
    wall_ms: DurationMs
    simulated_ms: DurationMs
    environment_ticks: Counter
    claim_status: ClaimStatus
    benchmark_report_id: SafeId | None


class BenchmarkMetrics(Contract):
    scheduled_episodes: Annotated[JsonInteger, Field(ge=1, le=1_000_000)]
    success_fraction: UnitFloat
    wrong_pad_fraction: UnitFloat
    timeout_fraction: UnitFloat
    infrastructure_failures: Annotated[JsonInteger, Field(ge=0, le=1_000_000)]
    mean_steps_all_episodes: Annotated[float, Field(ge=0, le=1_000_000, allow_inf_nan=False)]
    total_wall_ms: DurationMs


class Uncertainty(Contract):
    method: Literal["paired_layout_bootstrap", "not_estimated"]
    confidence_level: Literal[0.95]
    lower: ActionFloat
    upper: ActionFloat


class BenchmarkReport(Contract):
    report_id: SafeId
    preregistration_sha256: Sha256
    source_tree_sha256: Sha256
    model_sha256: Sha256
    checkpoint_sha256: Sha256
    cohorts: Annotated[list[SafeId], Field(min_length=1, max_length=1024)]
    layouts: Annotated[list[SafeId], Field(min_length=1, max_length=4096)]
    seeds: Annotated[list[Seed], Field(min_length=1, max_length=4096)]
    metrics: BenchmarkMetrics
    uncertainty: Uncertainty
    limitations: Annotated[list[Annotated[str, Field(min_length=1, max_length=1024)]], Field(min_length=1, max_length=32)]
    claim_status: ClaimStatus


class Capabilities(Contract):
    fixture: bool
    real_model_available: bool
    admission: Literal["unavailable", "closed", "open"]
    learning_claim_status: ClaimStatus
    approved_checkpoint_ids: Annotated[list[SafeId], Field(max_length=32)]
    approved_comparison_ids: Annotated[list[SafeId], Field(max_length=32)]


class ErrorResponse(Contract):
    code: ErrorCode
    message: Annotated[str, Field(min_length=1, max_length=512)]
    retryable: bool


CONTRACTS = {
    model.__name__: model for model in (
        ChallengeSpec, RunRequest, RunRecord, Observation, ControllerOutput,
        FrameEvent, ReplayManifest, CheckpointRef, BenchmarkReport, Capabilities,
        ErrorResponse,
    )
}


def canonical_sha256(payload: dict[str, object]) -> str:
    """Hash UTF-8 sorted-key compact JSON; nonfinite values are never serializable.

    Challenge content hashes use validated ``ChallengeSpec`` fields with
    ``content_sha256`` omitted. This is the v1 Python canonicalization, not RFC 8785.
    """
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def create_challenge(payload: dict[str, object]) -> ChallengeSpec:
    """Validate un-hashed content and compute the authoritative v1 digest."""
    if "content_sha256" in payload:
        raise ValueError("Content digest is computed by the server")
    provisional = ChallengeSpec.model_validate({**payload, "content_sha256": "0" * 64})
    content = provisional.model_dump(exclude={"content_sha256"})
    return ChallengeSpec.model_validate({**content, "content_sha256": canonical_sha256(content)})


def verify_challenge_hash(challenge: ChallengeSpec) -> None:
    """Verify derived content integrity after wire-schema validation."""
    expected = canonical_sha256(challenge.model_dump(exclude={"content_sha256"}))
    if challenge.content_sha256 != expected:
        raise ValueError("Challenge content SHA-256 mismatch")
