"""OBS v1 wire contracts. Times are local monotonic milliseconds, never UTC.

These describe future pipeline boundaries; OBS00 implements only idle reads.
JSON Schema handles structural constraints; semantic checks are mirrored by the
browser parser and exercised with the same generated positive/negative corpus.
"""
from typing import Annotated, Literal, get_args, get_origin

from pydantic import BaseModel, ConfigDict, Field, model_validator

Count = Annotated[int, Field(ge=0, le=2**53-1)]
Epoch = Annotated[int, Field(ge=1, le=2**53-1)]
Id = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$", max_length=64)]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$", max_length=64)]
Label = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[^\x00-\x1f\x7f]+$")]
Millis = Annotated[float, Field(ge=0, le=2**53-1)]
Rate = Annotated[float, Field(ge=0, le=1e12)]
Byte = Annotated[int, Field(ge=0, le=255)]
Pixels = Annotated[list[Byte], Field(min_length=256, max_length=256)]
EvidenceKind = Literal["real", "fixture"]
State = Literal["idle", "previewing", "starting", "running", "stopping", "stopped", "source_lost", "failed", "limit_reached"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False, frozen=True)

    @model_validator(mode="before")
    @classmethod
    def literal_types(cls, value):
        # Pydantic Literal alone considers False == 0 and True == 1. JSON
        # Schema does not: retain that distinction at the Python boundary.
        if isinstance(value, dict):
            for name, field in cls.model_fields.items():
                if name in value and get_origin(field.annotation) is Literal:
                    options = get_args(field.annotation)
                    allowed = {type(option) for option in options}
                    if float in allowed:
                        allowed.add(int)
                    if type(value[name]) not in allowed:
                        raise ValueError(f"{name} has an invalid literal type")
        return value


class SourceFormat(Contract):
    pixel_format: Literal["RGB24", "BGR24", "YUYV", "NV12", "MJPEG"]
    width: Annotated[int, Field(ge=1, le=8192)]
    height: Annotated[int, Field(ge=1, le=8192)]
    fps: Annotated[float, Field(gt=0, le=240)]


class SourceCapability(Contract):
    schema_version: Literal["obs-source-1"]
    source_id: Id
    evidence_kind: EvidenceKind
    name: Label
    driver: Label | None
    backend: Literal["ffmpeg-v4l2", "synthetic"]
    capabilities: Annotated[list[Literal["video_capture", "streaming", "readwrite"]], Field(max_length=3)] | None
    formats: Annotated[list[SourceFormat], Field(max_length=128)] | None
    metadata_state: Literal["available", "partial", "unavailable"]
    producer_detection: Literal["unknown", "driver", "obs_readonly_monitor", "synthetic"]

    @model_validator(mode="after")
    def evidence_backend(self):
        if self.evidence_kind == "fixture":
            if self.backend != "synthetic" or self.producer_detection != "synthetic":
                raise ValueError("fixture sources require the synthetic backend and detection label")
        elif self.backend != "ffmpeg-v4l2" or self.producer_detection == "synthetic":
            raise ValueError("real source metadata cannot describe a synthetic backend or detector")
        return self


class FrameIdentity(Contract):
    schema_version: Literal["obs-frame-1"]
    source_id: Id
    session_id: Id
    generation: Epoch
    sequence: Count
    evidence_kind: EvidenceKind
    width: Annotated[int, Field(ge=1, le=8192)]
    height: Annotated[int, Field(ge=1, le=8192)]
    pixel_format: Literal["RGB24"]
    receipt_monotonic_ms: Millis
    source_timestamp_ms: Millis | None
    source_sequence: Count | None
    source_clock: Literal["unknown", "producer", "local_monotonic"]

    @model_validator(mode="after")
    def clock_known(self):
        if (self.source_clock == "unknown") != (self.source_timestamp_ms is None):
            raise ValueError("source timestamp requires an explicit clock; unknown timing must be null")
        return self


class EncoderConfig(Contract):
    schema_version: Literal["obs-encoder-1"] = "obs-encoder-1"
    encoder_id: Literal["obs-rgb-letterbox16-v1"] = "obs-rgb-letterbox16-v1"
    size: Literal[16] = 16
    grayscale: Literal["(77R+150G+29B+128)//256"] = "(77R+150G+29B+128)//256"
    resampler: Literal["nearest-pixel-center"] = "nearest-pixel-center"
    padding_u8: Literal[0] = 0
    color: Literal["full-range-rgb-bt601-conversion"] = "full-range-rgb-bt601-conversion"


class MotorRates(Contract):
    steer_L: Rate
    steer_R: Rate
    fwd_L: Rate
    fwd_R: Rate
    back: Rate
    stop: Rate
    click: Rate


class RawAction(Contract):
    dx: Annotated[float, Field(ge=-1e12, le=1e12)]
    dy: Annotated[float, Field(ge=-1e12, le=1e12)]
    click: bool


class NeuralSample(Contract):
    schema_version: Literal["obs-neural-1"]
    response_id: Id
    frame: FrameIdentity
    observation_u8: Pixels
    encoder_id: Literal["obs-rgb-letterbox16-v1"]
    model_id: Id
    step_index: Annotated[int, Field(ge=0, le=511)]
    completed_monotonic_ms: Millis
    neural_ms: Literal[20.0]
    neural_state_mode: Literal["windowed_reset"]
    motor_rates_hz: MotorRates
    raw_action: RawAction

    @model_validator(mode="after")
    def time_order(self):
        if self.completed_monotonic_ms < self.frame.receipt_monotonic_ms:
            raise ValueError("response completion precedes input receipt")
        return self


class FlightControls(Contract):
    """Decoder output only; source pixels and world targets are excluded."""
    schema_version: Literal["obs-controls-1"]
    decoder_id: Literal["motor-flight-v1"]
    response_id: Id
    session_id: Id
    generation: Epoch
    evidence_kind: EvidenceKind
    issued_monotonic_ms: Millis
    expires_monotonic_ms: Millis
    yaw_rate_rad_s: Annotated[float, Field(ge=-3.141592653589793, le=3.141592653589793)]
    pitch_target_rad: Annotated[float, Field(ge=-0.7853981633974483, le=0.7853981633974483)]
    speed_target_units_s: Annotated[float, Field(ge=0, le=10)]

    @model_validator(mode="after")
    def expiry(self):
        if not 0 <= self.expires_monotonic_ms - self.issued_monotonic_ms <= 2000:
            raise ValueError("control lifetime must be within 2000 ms")
        return self


Coordinate = Annotated[float, Field(ge=-1e9, le=1e9)]
Vector3 = Annotated[list[Coordinate], Field(min_length=3, max_length=3)]


class FlightSnapshot(Contract):
    schema_version: Literal["obs-flight-1"]
    session_id: Id
    generation: Epoch
    evidence_kind: EvidenceKind
    tick: Count
    position: Vector3
    yaw_rad: Annotated[float, Field(ge=-3.141592653589793, le=3.141592653589793)]
    pitch_rad: Annotated[float, Field(ge=-0.7853981633974483, le=0.7853981633974483)]
    speed_units_s: Annotated[float, Field(ge=0, le=10)]
    applied_response_id: Id | None
    neutral: bool


class SyntheticFlightPreview(Contract):
    schema_version: Literal["obs-flight-preview-1"]
    evidence_kind: Literal["synthetic"]
    dt_ms: Literal[20]
    snapshots: Annotated[list[FlightSnapshot], Field(min_length=2, max_length=601)]

    @model_validator(mode="after")
    def sequence(self):
        first = self.snapshots[0]
        for tick, snapshot in enumerate(self.snapshots):
            if (snapshot.tick != tick or snapshot.evidence_kind != "fixture"
                    or (snapshot.session_id, snapshot.generation) != (first.session_id, first.generation)):
                raise ValueError("synthetic preview requires sequential fixture snapshots of one session")
        return self


class SessionConfig(Contract):
    schema_version: Literal["obs-session-config-1"] = "obs-session-config-1"
    source_id: Id
    evidence_kind: EvidenceKind
    seed: Annotated[int, Field(ge=0, le=2**32-1)]
    recording: bool = False
    duration_seconds: Annotated[int, Field(ge=1, le=120)] = 120
    max_model_calls: Annotated[int, Field(ge=1, le=512)] = 512
    source_deadline_ms: Annotated[int, Field(ge=1, le=2000)] = 2000
    step_deadline_ms: Annotated[int, Field(ge=1, le=5000)] = 5000
    startup_deadline_ms: Annotated[int, Field(ge=1, le=30000)] = 30000
    response_max_age_ms: Annotated[int, Field(ge=1, le=2000)] = 2000
    lease_ms: Annotated[int, Field(ge=1, le=3000)] = 3000
    stop_grace_ms: Annotated[int, Field(ge=1, le=3000)] = 3000
    recording_max_bytes: Annotated[int, Field(ge=1, le=33554432)] = 33554432
    fixed_step_ms: Literal[20] = 20
    encoder: EncoderConfig = EncoderConfig()
    decoder_id: Literal["motor-flight-v1"] = "motor-flight-v1"
    neural_state_mode: Literal["windowed_reset"] = "windowed_reset"
    learning_enabled: Literal[False] = False


class SessionStatus(Contract):
    schema_version: Literal["obs-session-status-1"]
    session_id: Id
    generation: Epoch
    evidence_kind: EvidenceKind
    state: State
    reason: Label | None
    attempted_calls: Annotated[int, Field(ge=0, le=512)]
    accepted_frames: Count
    overwritten_frames: Count
    content_unchanged_ms: Millis
    producer_health: Literal["unknown", "active", "inactive"]
    last_frame_sequence: Count | None
    last_response_id: Id | None


class StreamEnvelope(Contract):
    schema_version: Literal["obs-stream-1"]
    event_sequence: Count
    sent_monotonic_ms: Millis
    status: SessionStatus
    latest_source_frame: FrameIdentity | None
    neural_sample: NeuralSample | None
    flight: FlightSnapshot | None

    @model_validator(mode="after")
    def identity(self):
        objects = [self.latest_source_frame, self.neural_sample.frame if self.neural_sample else None, self.flight]
        for obj in objects:
            if obj and any(getattr(obj, key) != getattr(self.status, key)
                           for key in ("session_id", "generation", "evidence_kind")):
                raise ValueError("stream contains a foreign session, generation or evidence kind")
        if (self.latest_source_frame and self.neural_sample
                and self.latest_source_frame.source_id != self.neural_sample.frame.source_id):
            raise ValueError("a stream generation cannot switch sources")
        return self


class Provenance(Contract):
    source_head: Annotated[str, Field(pattern=r"^[0-9a-f]{40}$", max_length=40)]
    source_tree_sha256: Digest
    graph_sha256: Digest
    annotations_sha256: Digest
    checkpoint_sha256: Digest
    model_source_sha256: Digest
    model_config_sha256: Digest
    backend_version: Label
    python_version: Label
    numpy_version: Label
    scipy_version: Label
    model_id: Id
    neural_state_mode: Literal["windowed_reset"]
    gains: Literal["all-one-float32"]
    learning_enabled: Literal[False]


class ReplayManifest(Contract):
    schema_version: Literal["obs-replay-1"]
    session_id: Id
    generation: Epoch
    evidence_kind: EvidenceKind
    state: Literal["partial", "aborted", "complete"]
    config: SessionConfig
    source: SourceCapability
    initial_flight: FlightSnapshot
    provenance: Provenance
    events_sha256: Digest
    event_count: Count
    events_bytes: Annotated[int, Field(ge=0, le=33554432)]
    events_file: Literal["events.jsonl"]

    @model_validator(mode="after")
    def consistent(self):
        if not self.config.recording:
            raise ValueError("replay requires recording consent")
        if self.events_bytes > self.config.recording_max_bytes:
            raise ValueError("replay exceeds configured recording cap")
        if self.config.source_id != self.source.source_id:
            raise ValueError("replay source must match approved config")
        if any(obj.evidence_kind != self.evidence_kind for obj in (self.config, self.source, self.initial_flight)):
            raise ValueError("replay evidence labels disagree")
        if (self.initial_flight.session_id, self.initial_flight.generation, self.initial_flight.tick) != (
                self.session_id, self.generation, 0):
            raise ValueError("replay initial state must be tick zero of this session generation")
        return self


class LiveHealth(Contract):
    schema_version: Literal["obs-health-1"] = "obs-health-1"
    status: Literal["ok"] = "ok"
    phase: Literal["OBS00"] = "OBS00"
    state: Literal["idle"] = "idle"
    capture_implemented: Literal[False] = False
    inference_implemented: Literal[False] = False


class LiveConfig(Contract):
    schema_version: Literal["obs-config-1"] = "obs-config-1"
    phase: Literal["OBS00"] = "OBS00"
    capture_implemented: Literal[False] = False
    inference_implemented: Literal[False] = False
    recording_default: Literal[False] = False
    source_selection_required: Literal[True] = True
    validation_call_cap: Literal[1024] = 1024
    backend: Literal["ffmpeg-v4l2"] = "ffmpeg-v4l2"
    encoder: EncoderConfig = EncoderConfig()


CONTRACTS = {cls.__name__: cls for cls in (SourceCapability, FrameIdentity, EncoderConfig,
    NeuralSample, FlightControls, FlightSnapshot, SyntheticFlightPreview, SessionConfig, SessionStatus, StreamEnvelope,
    ReplayManifest, LiveHealth, LiveConfig)}
