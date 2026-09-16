"""Strict local control protocol; browser receives durations, never clock offsets."""
from typing import Annotated, Literal
import base64

from pydantic import Field, model_validator

from .contracts import (Contract, Count, Epoch, FrameIdentity, Id, Millis, NeuralSample,
                        Pixels, SessionConfig, SessionStatus, SourceCapability, StreamEnvelope)

Token = Annotated[str, Field(pattern=r"^[0-9a-f]{32}$", max_length=32)]
RECORDING_NOTICE = ("Recording is optional and off by default. Consent saves private processed 16x16 inputs, "
                    "raw neural responses and flight replay locally. These inputs can contain sensitive content. "
                    "Full-resolution source video is never saved.")


class StartRequest(Contract):
    schema_version: Literal["obs-start-1"] = "obs-start-1"
    request_id: Token
    owner_token: Token
    config: SessionConfig
    recording_consent: bool = False

    @model_validator(mode="after")
    def consent(self):
        if self.config.recording != self.recording_consent:
            raise ValueError("recording requires explicit consent for this Start")
        return self


class OwnerRequest(Contract):
    generation: Epoch
    owner_token: Token


class PreviewRequest(Contract):
    schema_version: Literal["obs-preview-request-1"] = "obs-preview-request-1"
    request_id: Token
    owner_token: Token
    source_id: Id
    duration_seconds: Annotated[int, Field(ge=1, le=30)] = 15


class SourceList(Contract):
    schema_version: Literal["obs-sources-1"] = "obs-sources-1"
    sources: Annotated[list[SourceCapability], Field(max_length=128)]


class InspectRequest(Contract):
    source_id: Id


class ControlBootstrap(Contract):
    schema_version: Literal["obs-control-1"] = "obs-control-1"
    csrf_token: Annotated[str, Field(pattern=r"^[0-9a-f]{32}\.[0-9a-f]{64}$", max_length=97)]
    recording_notice: Literal[RECORDING_NOTICE] = RECORDING_NOTICE


class SourcePreview(Contract):
    frame: FrameIdentity
    width: Annotated[int, Field(ge=1, le=320)]
    height: Annotated[int, Field(ge=1, le=180)]
    rgb_base64: Annotated[str, Field(max_length=230400, pattern=r"^[A-Za-z0-9+/]*={0,2}$")]
    observation_u8: Pixels

    @model_validator(mode="after")
    def pixel_count(self):
        if len(base64.b64decode(self.rgb_base64, validate=True)) != self.width*self.height*3:
            raise ValueError("preview RGB byte count disagrees with dimensions")
        return self


class DisplayFrame(Contract):
    """Presentation only: compressed color never enters a neural/replay envelope."""
    schema_version: Literal["screen-gremlin-display-1"] = "screen-gremlin-display-1"
    frame: FrameIdentity
    width: Annotated[int, Field(ge=1, le=960)]
    height: Annotated[int, Field(ge=1, le=540)]
    mime_type: Literal["image/jpeg"] = "image/jpeg"
    jpeg_base64: Annotated[str, Field(max_length=349528, pattern=r"^[A-Za-z0-9+/]*={0,2}$")]
    encoded_bytes: Annotated[int, Field(ge=4, le=262144)]
    delivered_monotonic_ms: Millis
    receipt_age_ms: Millis

    @model_validator(mode="after")
    def image_bounds(self):
        from io import BytesIO
        from PIL import Image
        data = base64.b64decode(self.jpeg_base64, validate=True)
        if len(data) != self.encoded_bytes or not data.startswith(b"\xff\xd8") or not data.endswith(b"\xff\xd9"):
            raise ValueError("display JPEG byte count or signature is invalid")
        try:
            with Image.open(BytesIO(data)) as image:
                if image.format != "JPEG" or image.size != (self.width, self.height):
                    raise ValueError("display JPEG dimensions disagree")
        except OSError as exc:
            raise ValueError("invalid display JPEG") from exc
        if self.width > self.frame.width or self.height > self.frame.height:
            raise ValueError("display frames cannot invent source resolution")
        if abs(self.width*self.frame.height - self.height*self.frame.width) > max(self.frame.width, self.frame.height):
            raise ValueError("display frame must preserve source aspect ratio")
        if self.delivered_monotonic_ms < self.frame.receipt_monotonic_ms:
            raise ValueError("display delivery predates source receipt")
        return self


class DisplayReply(Contract):
    schema_version: Literal["screen-gremlin-display-reply-1"] = "screen-gremlin-display-reply-1"
    status: SessionStatus
    latest: DisplayFrame | None

    @model_validator(mode="after")
    def identity(self):
        if self.latest:
            if any(getattr(self.latest.frame, key) != getattr(self.status, key)
                   for key in ("session_id", "generation", "evidence_kind")):
                raise ValueError("foreign display frame")
            if self.status.state not in {"previewing", "starting", "running"}:
                raise ValueError("inactive session cannot retain a display frame")
        return self


class ApiSnapshot(StreamEnvelope):
    schema_version: Literal["obs-api-snapshot-1"] = "obs-api-snapshot-1"
    kind: Literal["session", "preview"]
    lease_remaining_ms: Annotated[float, Field(ge=0, le=3000)]
    source_receipt_age_ms: Millis | None
    response_age_ms: Millis | None
    last_inferred: NeuralSample | None
    completed_calls: Annotated[int, Field(ge=0, le=512)]
    rejected_results: Count
    model_hz: Annotated[float, Field(ge=0, le=1e6)]
    capture_hz: Annotated[float, Field(ge=0, le=1e6)]
    model_mode: Literal["real", "fixture", "none"]
    last_step_wall_ms: Millis | None
    recording_id: Token | None
    recording_state: Literal["off", "partial", "aborted", "complete"]

    @model_validator(mode="after")
    def historical_identity(self):
        if self.last_inferred:
            for key in ("session_id", "generation", "evidence_kind"):
                if getattr(self.last_inferred.frame, key) != getattr(self.status, key):
                    raise ValueError("foreign historical observation")
            if (self.latest_source_frame and
                    self.last_inferred.frame.source_id != self.latest_source_frame.source_id):
                raise ValueError("historical observation source disagrees with capture")
        if self.neural_sample is not None and self.neural_sample != self.last_inferred:
            raise ValueError("active and historical neural observations disagree")
        if self.kind == "preview":
            if (self.model_mode != "none" or self.neural_sample is not None or self.last_inferred is not None
                    or self.flight is not None or self.completed_calls != 0 or self.status.attempted_calls != 0
                    or self.recording_state != "off" or self.recording_id is not None):
                raise ValueError("capture-only preview cannot contain model or recording state")
        elif self.model_mode == "none":
            raise ValueError("neural session must identify its model mode")
        return self


class ServiceStatus(Contract):
    schema_version: Literal["obs-service-status-1"] = "obs-service-status-1"
    current: ApiSnapshot | None


class PreviewReply(Contract):
    schema_version: Literal["obs-source-preview-1"] = "obs-source-preview-1"
    status: SessionStatus
    latest: SourcePreview | None

    @model_validator(mode="after")
    def identity(self):
        if self.latest and any(getattr(self.latest.frame, key) != getattr(self.status, key)
                               for key in ("session_id", "generation", "evidence_kind")):
            raise ValueError("foreign preview frame")
        return self


API_CONTRACTS = {cls.__name__: cls for cls in (StartRequest, OwnerRequest, PreviewRequest,
    SourceList, InspectRequest, ControlBootstrap, SourcePreview, DisplayFrame, DisplayReply,
    ApiSnapshot, ServiceStatus, PreviewReply)}
