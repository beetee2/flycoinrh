"""Opt-in private processed-input recordings and pure, verified flight replay.

Only typed 16x16 observations enter this module. It has no capture, model,
accounting, subprocess or network dependency. IDs and filenames are generated here.
"""
import hashlib
import json
import os
from contextlib import suppress
from itertools import islice
from pathlib import Path
import re
import stat
import uuid
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .contracts import (Contract, FrameIdentity, NeuralSample, Pixels, Provenance,
                        ReplayManifest, SessionConfig, SourceCapability, Id)
from .flight import FlightState, FlightTrace, decode, replay
from .neural import StepResult

MAX_BYTES = 32 * 1024 * 1024
MANIFEST_RESERVE = 16384
ID_PATTERN = re.compile(r"[0-9a-f]{32}\Z")
RecordingId = Annotated[str, Field(pattern=r"^[0-9a-f]{32}$", max_length=32)]


class RecordingError(ValueError):
    """Invalid, unavailable, incomplete or corrupted private recording."""


class InputEvent(Contract):
    kind: Literal["input"] = "input"
    frame: FrameIdentity
    observation_u8: Pixels
    step_index: Annotated[int, Field(ge=0, le=511)]
    encoder_id: Literal["obs-rgb-letterbox16-v1"] = "obs-rgb-letterbox16-v1"


class SampleEvent(Contract):
    kind: Literal["sample"] = "sample"
    sample: NeuralSample
    result: StepResult


class TraceEvent(Contract):
    kind: Literal["trace"] = "trace"
    trace: FlightTrace
    final: FlightState


class ManifestEnvelope(Contract):
    schema_version: Literal["obs-replay-envelope-1"] = "obs-replay-envelope-1"
    recording_id: RecordingId
    manifest: ReplayManifest
    sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class ReplayPayload(Contract):
    schema_version: Literal["obs-recorded-replay-1"] = "obs-recorded-replay-1"
    manifest: ReplayManifest
    inputs: Annotated[list[InputEvent], Field(max_length=512)]
    samples: Annotated[list[NeuralSample], Field(max_length=512)]
    results: Annotated[list[StepResult], Field(max_length=512)]
    trace: FlightTrace
    final: FlightState

    @model_validator(mode="after")
    def flight_identity(self):
        if (self.manifest.initial_flight != self.trace.initial.snapshot
                or self.trace.initial.physics_id != self.final.physics_id):
            raise ValueError("replay flight physics or initial state mismatch")
        return self


class ReplayListEntry(Contract):
    recording_id: RecordingId
    manifest: ReplayManifest | None = None
    state: Literal["partial", "aborted"] | None = None
    error: Literal["Recording unavailable or corrupted."] | None = None

    @model_validator(mode="after")
    def one_state(self):
        if sum(value is not None for value in (self.manifest, self.state, self.error)) != 1:
            raise ValueError("recording entry requires exactly one manifest, reservation state or error")
        return self


class ReplayList(Contract):
    schema_version: Literal["obs-replay-list-1"] = "obs-replay-list-1"
    recordings: Annotated[list[ReplayListEntry], Field(max_length=128)]


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _private_directory(path):
    path = Path(path).absolute()
    for part in (path, *path.parents):
        if part.is_symlink():
            raise RecordingError("recording path cannot contain symlinks")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not path.is_dir() or stat.S_IMODE(path.stat().st_mode) != 0o700:
        raise RecordingError("recording directory must have private permissions")
    return path


def _read(path, limit):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600 or info.st_size > limit:
            raise RecordingError("recording file type, permissions or byte bound invalid")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read(limit + 1)
        if len(data) > limit:
            raise RecordingError("recording byte bound exceeded")
        return data
    finally:
        os.close(fd)


def _sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _storage_bytes(directory):
    # At most seven owned files coexist during atomic transitions. Do not scan an
    # unbounded or externally populated directory while checking a private write.
    paths = list(islice(directory.iterdir(), 8))
    allowed = {"events.jsonl", "manifest.json", "manifest.json.tmp", "complete.sha256",
               "complete.sha256.tmp", "reservation.json", "reservation.json.tmp"}
    if len(paths) > 7 or any(path.name not in allowed for path in paths):
        raise RecordingError("recording contains unexpected files")
    total = 0
    for path in paths:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600:
            raise RecordingError("recording file type or permissions invalid")
        total += info.st_size
    return total


def _atomic(path, data, *, max_bytes):
    # Both the old destination and the new temporary file exist before rename.
    # Include reservation, events, manifest, completion seal and any temp files.
    if _storage_bytes(path.parent) + len(data) > max_bytes:
        raise RecordingError("recording total byte cap reached")
    temporary = path.with_name(path.name + ".tmp")
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(data)
            stream.flush()
            os.fsync(fd)
        os.replace(temporary, path)
        _sync_directory(path.parent)
    finally:
        os.close(fd)
        temporary.unlink(missing_ok=True)


class VerifiedReplay:
    def __init__(self, manifest, events):
        self.manifest = manifest
        self.inputs, self.samples, self.results = [], [], []
        self.trace = None
        self.states = []
        if (manifest.initial_flight.speed_units_s != 0 or not manifest.initial_flight.neutral
                or manifest.initial_flight.applied_response_id is not None):
            raise RecordingError("recording must start with neutral flight")
        session = (manifest.session_id, manifest.generation, manifest.evidence_kind)
        by_response = {}
        pending = None
        previous_sequence = -1
        for event in events:
            if self.trace is not None:
                raise RecordingError("events after final trace")
            if isinstance(event, InputEvent):
                if pending is not None or event.step_index != len(self.inputs):
                    raise RecordingError("input step ordering mismatch")
                frame = event.frame
                if ((frame.session_id, frame.generation, frame.evidence_kind) != session
                        or frame.source_id != manifest.source.source_id
                        or frame.sequence <= previous_sequence):
                    raise RecordingError("input metadata mismatch")
                previous_sequence = frame.sequence
                pending = event
                self.inputs.append(event)
            elif isinstance(event, SampleEvent):
                sample = event.sample
                result = event.result
                if ((result.session_id, result.generation, result.step_index) != (
                        sample.frame.session_id, sample.frame.generation, sample.step_index)
                        or result.completed_monotonic_ms != sample.completed_monotonic_ms
                        or result.motor_rates_hz != sample.motor_rates_hz or result.raw_action != sample.raw_action
                        or result.output.telemetry.neural_ms != sample.neural_ms
                        or result.output.model_mode != ("fixture" if manifest.provenance.model_id.startswith("fixture-")
                                                        else "windowed_reset")
                        or (manifest.evidence_kind == "real" and result.output.model_mode == "fixture")):
                    raise RecordingError("raw worker response metadata mismatch")
                if (pending is None or sample.step_index != pending.step_index
                        or sample.frame != pending.frame or sample.observation_u8 != pending.observation_u8
                        or sample.encoder_id != pending.encoder_id
                        or sample.model_id != manifest.provenance.model_id
                        or sample.response_id in by_response):
                    raise RecordingError("response/input metadata mismatch")
                self.samples.append(sample)
                self.results.append(result)
                by_response[sample.response_id] = sample
                pending = None
            else:
                trace = event.trace
                if trace.initial.snapshot != manifest.initial_flight:
                    raise RecordingError("flight initial state mismatch")
                if trace.initial.physics_id != event.final.physics_id:
                    raise RecordingError("flight physics identity mismatch")
                if trace.decoder_id != manifest.config.decoder_id or trace.ticks > manifest.config.duration_seconds*50:
                    raise RecordingError("flight configuration mismatch")
                for application in trace.events:
                    controls = application.controls
                    if controls is None:
                        continue
                    sample = by_response.get(controls.response_id)
                    if sample is None:
                        raise RecordingError("control lacks recorded neural response")
                    expected = decode(sample.motor_rates_hz, response_id=sample.response_id,
                        session_id=manifest.session_id, generation=manifest.generation,
                        evidence_kind=manifest.evidence_kind,
                        receipt_ms=sample.frame.receipt_monotonic_ms,
                        completed_ms=sample.completed_monotonic_ms, now_ms=controls.issued_monotonic_ms,
                        max_age_ms=float(manifest.config.response_max_age_ms))
                    if expected != controls:
                        raise RecordingError("control/decoder metadata mismatch")
                self.states = replay(trace.initial, trace.events, ticks=trace.ticks,
                                     origin_ms=trace.origin_ms, terminal_tick=trace.terminal_tick)
                if self.states[-1] != event.final:
                    raise RecordingError("recorded flight state disagrees with control replay")
                self.trace = trace
        if len(self.inputs) > manifest.config.max_model_calls:
            raise RecordingError("recorded model-call bound exceeded")
        if manifest.state == "complete" and self.trace is None:
            raise RecordingError("complete recording lacks verified final trace")

    def payload(self):
        if self.trace is None or self.manifest.state != "complete":
            raise RecordingError("recording is incomplete")
        return ReplayPayload(manifest=self.manifest, inputs=self.inputs, samples=self.samples,
                             results=self.results, trace=self.trace, final=self.states[-1])

    def seek(self, tick):
        if type(tick) is not int or not 0 <= tick < len(self.states):
            raise RecordingError("seek tick out of bounds")
        return self.states[tick].model_copy(deep=True)


class RecordingStore:
    def __init__(self, root):
        # Constructing/read-only API use does not create storage or start work.
        self.root = Path(root).absolute()

    def _directory(self, recording_id):
        if not isinstance(recording_id, str) or not ID_PATTERN.fullmatch(recording_id):
            raise RecordingError("invalid recording ID")
        path = self.root / recording_id
        if not path.exists():
            raise RecordingError("recording unavailable")
        return _private_directory(path)

    def start(self, config: SessionConfig, source: SourceCapability, provenance: Provenance,
              initial: FlightState):
        config = SessionConfig.model_validate(config.model_dump())
        if not config.recording:
            raise RecordingError("recording requires explicit opt-in")
        if config.recording_max_bytes < MANIFEST_RESERVE:
            raise RecordingError("recording byte cap cannot hold manifest")
        root = _private_directory(self.root)
        return Recorder(root, config, source, provenance, initial)

    def reserve(self, config, source, session_id, generation):
        if not config.recording:
            raise RecordingError("recording requires explicit opt-in")
        if config.recording_max_bytes < MANIFEST_RESERVE:
            raise RecordingError("recording byte cap cannot hold manifest")
        return Reservation(_private_directory(self.root), config, source, session_id, generation)

    def manifest(self, recording_id):
        directory = self._directory(recording_id)
        data = _read(directory / "manifest.json", MANIFEST_RESERVE)
        envelope = ManifestEnvelope.model_validate_json(data)
        if envelope.recording_id != recording_id:
            raise RecordingError("recording directory identity mismatch")
        if envelope.sha256 != _hash(_json({"recording_id": envelope.recording_id,
                                          "manifest": envelope.manifest.model_dump(mode="json")})):
            raise RecordingError("manifest hash mismatch")
        if _storage_bytes(directory) > envelope.manifest.config.recording_max_bytes:
            raise RecordingError("recording total byte cap reached")
        if envelope.manifest.state == "complete":
            seal = _read(directory / "complete.sha256", 64)
            if seal != _hash(data).encode("ascii"):
                raise RecordingError("completion seal mismatch")
        return envelope.manifest

    def list(self):
        if not self.root.exists():
            return []
        _private_directory(self.root)
        result = []
        paths = list(islice(self.root.iterdir(), 129))
        if len(paths) > 128:
            raise RecordingError("recording listing exceeds 128 entries; inspect private storage locally")
        for path in sorted(paths):
            if ID_PATTERN.fullmatch(path.name):
                try:
                    if not (path / "manifest.json").exists():
                        reservation = ReservationState.model_validate_json(
                            _read(self._directory(path.name) / "reservation.json", MANIFEST_RESERVE))
                        if reservation.recording_id != path.name:
                            raise RecordingError("reservation directory identity mismatch")
                        if _storage_bytes(path) > reservation.config.recording_max_bytes:
                            raise RecordingError("reservation total byte cap reached")
                        result.append({"recording_id": path.name, "state": reservation.state})
                    else:
                        manifest = self.manifest(path.name)
                        if manifest.state == "complete":
                            manifest = self.read(path.name).manifest
                        result.append({"recording_id": path.name, "manifest": manifest})
                except (OSError, ValueError):
                    # Corrupted/unpublished artifacts are visible as errors, never complete.
                    result.append({"recording_id": path.name, "error": "Recording unavailable or corrupted."})
        return result

    def read(self, recording_id):
        manifest = self.manifest(recording_id)
        if manifest.state != "complete":
            raise RecordingError("recording is partial or aborted")
        data = _read(self._directory(recording_id) / "events.jsonl", manifest.config.recording_max_bytes)
        if (len(data) != manifest.events_bytes or _hash(data) != manifest.events_sha256
                or len(data) + MANIFEST_RESERVE > manifest.config.recording_max_bytes):
            raise RecordingError("events hash or byte bound mismatch")
        lines = data.splitlines()
        if len(lines) != manifest.event_count or (data and not data.endswith(b"\n")):
            raise RecordingError("event count or framing mismatch")
        events = []
        classes = {"input": InputEvent, "sample": SampleEvent, "trace": TraceEvent}
        for line in lines:
            value = json.loads(line)
            if not isinstance(value, dict) or value.get("kind") not in classes:
                raise RecordingError("unsupported recording event")
            events.append(classes[value["kind"]].model_validate(value))
        return VerifiedReplay(manifest, events)


class Recorder:
    def __init__(self, root, config, source, provenance, initial, recording_id=None):
        self.recording_id = recording_id or uuid.uuid4().hex
        self.directory = root / self.recording_id
        self.directory.mkdir(mode=0o700, exist_ok=recording_id is not None)
        self._closed = False
        self._events = []
        self._digest = hashlib.sha256()
        self.manifest = ReplayManifest(schema_version="obs-replay-1", session_id=initial.snapshot.session_id,
            generation=initial.snapshot.generation, evidence_kind=initial.snapshot.evidence_kind,
            state="partial", config=config, source=source, initial_flight=initial.snapshot,
            provenance=provenance, events_sha256=self._digest.hexdigest(), event_count=0,
            events_bytes=0, events_file="events.jsonl")
        self._fd = os.open(self.directory / "events.jsonl", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.fsync(self._fd)
            self._publish()
            _sync_directory(root)
        except BaseException:
            os.close(self._fd)
            self._closed = True
            raise

    def _publish(self):
        payload = {"recording_id": self.recording_id, "manifest": self.manifest.model_dump(mode="json")}
        data = _json(ManifestEnvelope(recording_id=self.recording_id, manifest=self.manifest,
                                      sha256=_hash(_json(payload))).model_dump(mode="json"))
        if len(data) * 2 + 128 > MANIFEST_RESERVE:
            raise RecordingError("manifest byte bound exceeded")
        _atomic(self.directory / "manifest.json", data, max_bytes=self.manifest.config.recording_max_bytes)

    def _append(self, event):
        if self._closed:
            raise RecordingError("recording is closed")
        data = _json(event.model_dump(mode="json")) + b"\n"
        try:
            if self.manifest.events_bytes + len(data) + MANIFEST_RESERVE > self.manifest.config.recording_max_bytes:
                raise RecordingError("recording byte cap reached")
            remaining = memoryview(data)
            while remaining:
                written = os.write(self._fd, remaining)
                if written <= 0:
                    raise OSError("recording write made no progress")
                remaining = remaining[written:]
            os.fsync(self._fd)
            self._digest.update(data)
            self._events.append(event)
            self.manifest = self.manifest.model_copy(update={"events_sha256": self._digest.hexdigest(),
                "events_bytes": self.manifest.events_bytes + len(data), "event_count": len(self._events)})
            self._publish()
        except (OSError, ValueError):
            self.abort()
            raise

    def append_input(self, frame, observation_u8, step_index):
        self._append(InputEvent(frame=frame, observation_u8=observation_u8, step_index=step_index))

    def append_sample(self, sample, result):
        self._append(SampleEvent(sample=sample, result=result))

    def finish(self, trace, final, complete=True):
        if self._closed:
            raise RecordingError("recording is closed")
        try:
            self._append(TraceEvent(trace=trace, final=final))
            candidate = self.manifest.model_copy(update={"state": "complete" if complete else "aborted"})
            VerifiedReplay(candidate, self._events)
            self.manifest = candidate
            self._publish()
            if complete:
                manifest_bytes = _read(self.directory / "manifest.json", MANIFEST_RESERVE)
                _atomic(self.directory / "complete.sha256", _hash(manifest_bytes).encode("ascii"),
                        max_bytes=self.manifest.config.recording_max_bytes)
        except (OSError, ValueError):
            self.abort()
            raise
        finally:
            if not self._closed:
                os.close(self._fd)
                self._closed = True
        return self.manifest

    def abort(self):
        if self._closed:
            return
        with suppress(OSError):
            (self.directory / "complete.sha256").unlink(missing_ok=True)
        self.manifest = self.manifest.model_copy(update={"state": "aborted"})
        try:
            self._publish()
        except (OSError, ValueError):
            pass  # Last durable manifest remains partial; never claim completion.
        finally:
            os.close(self._fd)
            self._closed = True


class ReservationState(Contract):
    recording_id: RecordingId
    schema_version: Literal["obs-replay-reservation-1"] = "obs-replay-reservation-1"
    state: Literal["partial", "aborted"] = "partial"
    config: SessionConfig
    source: SourceCapability
    session_id: Id
    generation: Annotated[int, Field(ge=1, le=2**53-1)]


class Reservation:
    """Durable opt-in intent before model startup, without invented provenance."""
    def __init__(self, root, config, source, session_id, generation):
        self.recording_id = uuid.uuid4().hex
        self.directory = root / self.recording_id
        self.directory.mkdir(mode=0o700)
        self.state = ReservationState(recording_id=self.recording_id, config=config, source=source,
                                      session_id=session_id, generation=generation)
        if config.source_id != source.source_id or config.evidence_kind != source.evidence_kind:
            raise RecordingError("reservation source mismatch")
        self._publish()
        _sync_directory(root)

    def _publish(self):
        data = _json(self.state.model_dump(mode="json"))
        if len(data) * 2 > min(MANIFEST_RESERVE, self.state.config.recording_max_bytes):
            raise RecordingError("reservation byte cap reached")
        _atomic(self.directory / "reservation.json", data,
                max_bytes=self.state.config.recording_max_bytes)

    def initialize(self, provenance, initial):
        if self.state.state != "partial" or (initial.snapshot.session_id, initial.snapshot.generation) != (
                self.state.session_id, self.state.generation):
            raise RecordingError("reservation is aborted or initial identity mismatches")
        recorder = Recorder(self.directory.parent, self.state.config, self.state.source, provenance,
                            initial, recording_id=self.recording_id)
        try:
            (self.directory / "reservation.json").unlink()
            _sync_directory(self.directory)
        except OSError:
            recorder.abort()
            raise
        return recorder

    def abort(self):
        self.state = self.state.model_copy(update={"state": "aborted"})
        try:
            self._publish()
        except (OSError, ValueError):
            pass


def provenance_from_worker(identity, *, backend_version):
    """Project the worker's once-per-load source-bound identity into replay v1.

    Compound identity maps use canonical UTF-8 JSON (sorted keys, no whitespace).
    Hashes describe the live source set/model config set, not uninspected files.
    """
    model, runtime = identity["model"], identity["runtime"]
    return Provenance(source_head=identity["source_head"],
        source_tree_sha256=_hash(_json(identity["live_sources"])),
        graph_sha256=model["graph_sha256"], annotations_sha256=model["annotations_sha256"],
        checkpoint_sha256=model["checkpoint"]["sha256"],
        model_source_sha256=_hash(_json(model["model_source_sha256"])),
        model_config_sha256=_hash(_json({key: model[key] for key in (
            "parameters_sha256", "calibration_sha256", "parameters", "calibration")})),
        backend_version=backend_version, python_version=runtime["python"],
        numpy_version=runtime["numpy"], scipy_version=runtime["scipy"], model_id=identity["model_id"],
        neural_state_mode=model["neural_state_mode"], gains=model["gains"],
        learning_enabled=model["learning_enabled"])


RECORDING_CONTRACTS = {cls.__name__: cls for cls in (ReplayPayload, ReplayList, FlightState)}
