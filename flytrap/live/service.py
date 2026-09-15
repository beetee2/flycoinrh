"""One local control owner, bounded current-snapshot publication, idle by default."""
import asyncio
import base64
from collections import OrderedDict
from dataclasses import dataclass, field
from functools import partial
import secrets
import threading
import time
import uuid

from .accounting import BusyError, LiveOwnership
from .api_contracts import ApiSnapshot, PreviewReply, SourceList, SourcePreview
from .contracts import SessionConfig, SessionStatus, SourceCapability, SourceFormat


class NotFound(ValueError):
    pass


class Conflict(ValueError):
    pass


class Forbidden(ValueError):
    pass


class Unavailable(ValueError):
    pass


def source_metadata():
    from .environment import discover_devices
    return [row["capability"] for row in discover_devices()["devices"]][:128]


def safe_source_metadata():
    """Server-selected deterministic imagery; this does not select a fixture model."""
    return [SourceCapability(schema_version="obs-source-1", source_id="fixture-pattern",
        evidence_kind="fixture", name="Deterministic safe input (real neural model)", driver=None,
        backend="synthetic", capabilities=None, formats=[SourceFormat(
            pixel_format="RGB24", width=320, height=180, fps=30.)],
        metadata_state="available", producer_detection="synthetic")]


def neural_factory(config, *, repository_root, source, expected_device, recording_store,
                   execution_purpose="automated"):
    from .session import NeuralSession
    return NeuralSession(config, purpose=execution_purpose, repository_root=repository_root,
                         expected_device=expected_device, recording_store=recording_store, source=source)


class PreviewSession:
    """Lease-bounded capture only, sharing process exclusion with live/P00."""
    def __init__(self, config, *, repository_root, expected_device, capture_factory=None):
        from .capture import Capture
        self.config = config
        self.session_id, self.generation = uuid.uuid4().hex, 1
        self.capture = (capture_factory or Capture)(source_id=config.source_id, session_id=self.session_id,
            generation=1, duration_s=config.duration_seconds, expected_device=expected_device,
            verified=config.evidence_kind == "real")
        self.root = repository_root
        self._state, self._reason = "idle", None
        self._lease = 0.
        self._stop = threading.Event()
        self._done = threading.Event()
        self._lock = threading.RLock()
        self._thread = self._ownership = None

    def start(self):
        self._ownership = LiveOwnership(self.root).acquire()
        self._lease = time.monotonic()
        self._state = "previewing"
        self._thread = threading.Thread(target=self._run, daemon=True)
        try:
            self._thread.start()
        except Exception:
            self._ownership.close()
            raise
        return self

    def _run(self):
        try:
            self.capture.start()
            started = time.monotonic()
            while not self._stop.wait(.02):
                with self._lock:
                    if time.monotonic() - self._lease >= self.config.lease_ms/1000:
                        self._reason = "Control lease expired; explicit Preview required."
                        break
                if time.monotonic() - started >= self.config.duration_seconds:
                    break
                status = self.capture.status()
                if status.state != "previewing":
                    self._state, self._reason = status.state, status.reason
                    break
        except Exception:
            self._state, self._reason = "failed", "Selected source preview unavailable."
        finally:
            try:
                self.capture.stop()
            except Exception:
                self._state, self._reason = "failed", "Source cleanup failed; verifying resource closure."
            if not self.capture.wait_closed(3):
                self._state, self._reason = "failed", "Source cleanup incomplete; ownership retained."
                while not self.capture.wait_closed(.1):
                    pass
            self._ownership.close()
            if self._state in {"previewing", "stopping"}:
                self._state = "stopped"
            self._done.set()

    def renew_lease(self):
        with self._lock:
            if self._state != "previewing" or time.monotonic() - self._lease >= self.config.lease_ms/1000:
                self._stop.set()
                return False
            self._lease = time.monotonic()
            return True

    @property
    def lease_remaining_ms(self):
        with self._lock:
            return max(0., self.config.lease_ms-(time.monotonic()-self._lease)*1000) if self._state == "previewing" else 0.

    def stop(self):
        self._stop.set()
        self._done.wait(3)
        return self.status()

    def wait(self, timeout=None):
        return self._done.wait(timeout)

    def status(self):
        captured = self.capture.status()
        frame = self.capture.slot.latest()
        return SessionStatus(schema_version="obs-session-status-1", session_id=self.session_id,
            generation=1, evidence_kind=self.config.evidence_kind, state=self._state, reason=self._reason,
            attempted_calls=0, accepted_frames=captured.accepted_frames,
            overwritten_frames=captured.overwritten_frames, content_unchanged_ms=captured.content_unchanged_ms,
            producer_health="active" if captured.producer == "synthetic" else captured.producer,
            last_frame_sequence=frame.identity.sequence if frame else None, last_response_id=None)


@dataclass
class Entry:
    session: object
    owner_token: str
    request_id: str
    fingerprint: str
    kind: str
    sequence: int = 0
    rate_started: float = field(default_factory=time.monotonic)
    rate_frames: int = 0
    capture_hz: float = 0.


class LiveService:
    max_clients = 4
    max_sessions = 32
    max_requests = 256

    def __init__(self, *, repository_root=None, session_factory=None,
                 source_provider=source_metadata, capture_factory=None, recording_store=None,
                 execution_purpose="automated"):
        from pathlib import Path
        self.root = Path(repository_root) if repository_root is not None else Path(__file__).resolve().parents[2]
        if execution_purpose not in {"automated", "human"}:
            raise ValueError("execution purpose must be configured by the server")
        self.execution_purpose = execution_purpose
        self.session_factory = session_factory or partial(neural_factory, execution_purpose=execution_purpose)
        self.source_provider = source_provider
        self.capture_factory = capture_factory
        self.recording_store = recording_store
        self.sessions = OrderedDict()
        self.requests = {}
        self.current_id = None
        self._lock = threading.RLock()
        self._clients = {}
        self._dropped = 0
        self._task = None
        self._closed = False

    def sources(self):
        return SourceList(sources=self.source_provider())

    def config(self):
        from .accounting import LiveLedger, LedgerCorrupt
        from .contracts import LiveConfig
        ledger = LiveLedger.automated(self.root)
        count = 0
        if ledger.path.exists() or ledger.checkpoint.exists():
            try:
                count = ledger.attempted
            except (BusyError, LedgerCorrupt, OSError):
                count = None
        return LiveConfig(execution_purpose=self.execution_purpose, validation_attempted=count,
                          validation_remaining=None if count is None else ledger.cap-count)

    def _source(self, source_id):
        source = next((s for s in self.sources().sources if s.source_id == source_id), None)
        if source is None:
            raise Unavailable("Select an available source from source metadata.")
        device = None
        if source.evidence_kind == "real":
            from .device import inspect_selected
            try:
                device = inspect_selected(source.source_id)
            except (ValueError, OSError):
                raise Unavailable("Selected OBS source inspection failed; check metadata and access.") from None
            if device.producer_detection != "driver":
                raise Unavailable("Verified producer detection is unavailable; configure the selected OBS source.")
            source = SourceCapability(**{**source.model_dump(), "name": device.card, "driver": device.driver,
                "capabilities": ["video_capture", "streaming"], "metadata_state": "available",
                "producer_detection": "driver", "formats": [SourceFormat(
                    pixel_format={"RGB3": "RGB24", "BGR3": "BGR24", "YUYV": "YUYV", "NV12": "NV12"}[device.fourcc],
                    width=device.width, height=device.height, fps=device.fps)]})
        return source, device

    def inspect(self, source_id):
        return self._source(source_id)[0]

    def start(self, request, *, preview=False):
        # Threadpool request handlers serialize admission only. Inference and Stop
        # never hold this lock; busy responses/health remain prompt during work.
        with self._lock:
            if self._closed:
                raise Unavailable("Local service is shutting down.")
            fingerprint = request.model_dump_json()
            existing = self.requests.get(request.request_id)
            if existing:
                if existing[0] != fingerprint:
                    raise Conflict("Request ID was already used with different parameters.")
                return self.snapshot(existing[1])
            if len(self.requests) >= self.max_requests:
                raise Unavailable("Control request limit reached; restart the idle service explicitly.")
            if self.current_id and not self.sessions[self.current_id].session.wait(0):
                raise BusyError("One control session already owns the local source/model.")
            source_id = request.source_id if preview else request.config.source_id
            source, device = self._source(source_id)
            config = (SessionConfig(source_id=source_id, evidence_kind=source.evidence_kind, seed=0,
                duration_seconds=request.duration_seconds) if preview else request.config)
            if config.evidence_kind != source.evidence_kind:
                raise Conflict("Source and session evidence labels disagree.")
            if config.recording and source.evidence_kind == "real":
                raise Forbidden("Recording the selected OBS source is disabled; use the safe deterministic input.")
            if preview:
                session = PreviewSession(config, repository_root=self.root, expected_device=device,
                                         capture_factory=self.capture_factory)
            else:
                if config.recording and self.recording_store is None:
                    from .recording import RecordingStore
                    self.recording_store = RecordingStore(self.root / "artifacts/live/recordings")
                session = self.session_factory(config, repository_root=self.root, source=source,
                    expected_device=device, recording_store=self.recording_store)
            session.start()
            entry = Entry(session, request.owner_token, request.request_id, fingerprint,
                          "preview" if preview else "session")
            self.sessions[session.session_id] = entry
            self.current_id = session.session_id
            self.requests[request.request_id] = (fingerprint, session.session_id)
            while len(self.sessions) > self.max_sessions:
                self.sessions.popitem(last=False)
            return self.snapshot(session.session_id)

    def entry(self, session_id, generation=None):
        entry = self.sessions.get(session_id)
        if entry is None:
            raise NotFound("Session is unknown or no longer retained by this service.")
        if generation is not None and generation != entry.session.generation:
            raise Conflict("Session generation is stale.")
        return entry

    def control(self, session_id, request, *, stop=False):
        with self._lock:
            entry = self.entry(session_id, request.generation)
            if not secrets.compare_digest(entry.owner_token, request.owner_token):
                raise Forbidden("Only the control owner can renew or stop this session.")
        if stop:
            entry.session.stop()
        elif not entry.session.renew_lease():
            raise Conflict("Control lease ended; an explicit new Start is required.")
        return self.snapshot(session_id)

    def snapshot(self, session_id):
        with self._lock:
            entry = self.entry(session_id)
            session = entry.session
            frame = session.capture.slot.latest_preview()
            now = time.monotonic()*1000
            captured = session.capture.status()
            elapsed = now/1000-entry.rate_started
            if elapsed >= .25:
                entry.capture_hz = max(0., min(1e6, (captured.accepted_frames-entry.rate_frames)/elapsed))
                entry.rate_started, entry.rate_frames = now/1000, captured.accepted_frames
            if session.wait(0):
                entry.capture_hz = 0.
            entry.sequence += 1
            common = dict(event_sequence=entry.sequence, sent_monotonic_ms=now, kind=entry.kind,
                          latest_source_frame=frame.identity if frame else None,
                          lease_remaining_ms=session.lease_remaining_ms, capture_hz=entry.capture_hz,
                          model_mode="none" if entry.kind == "preview" else (
                              "fixture" if session.purpose == "fixture" else "real"))
            if entry.kind == "preview":
                return ApiSnapshot(**common, status=session.status(), neural_sample=None,
                    last_inferred=None, flight=None, completed_calls=0, rejected_results=0,
                    source_receipt_age_ms=max(0., now-frame.identity.receipt_monotonic_ms) if frame else None,
                    response_age_ms=None, model_hz=0., last_step_wall_ms=None,
                    recording_id=None, recording_state="off")
            snap = session.snapshot()
            return ApiSnapshot(**common, status=snap.status, neural_sample=snap.sample,
                last_inferred=snap.last_inferred, flight=snap.flight, completed_calls=snap.completed_calls,
                rejected_results=snap.rejected_results, source_receipt_age_ms=snap.source_receipt_age_ms,
                response_age_ms=max(0., now-snap.last_inferred.frame.receipt_monotonic_ms) if snap.last_inferred else None,
                model_hz=snap.model_hz, last_step_wall_ms=snap.last_step_wall_ms,
                recording_id=session.recording_id, recording_state=session.recording_state)

    def preview(self, session_id):
        from .encoding import preview_pair
        entry = self.entry(session_id)
        status = self.snapshot(session_id).status
        frame = entry.session.capture.slot.latest_preview()
        latest = None
        if frame is not None:
            pair = preview_pair(frame)
            latest = SourcePreview(frame=frame.identity, width=pair.source.width, height=pair.source.height,
                rgb_base64=base64.b64encode(pair.source.rgb).decode(), observation_u8=list(pair.encoded.u8))
        return PreviewReply(status=status, latest=latest)

    async def open(self):
        self._task = asyncio.create_task(self._publish())

    async def close(self):
        self._closed = True
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        for entry in list(self.sessions.values()):
            if not entry.session.wait(0):
                await asyncio.to_thread(entry.session.stop)
        self._clients.clear()

    async def _publish(self):
        while True:
            for client_id, (session_id, queue) in list(self._clients.items()):
                try:
                    snapshot = await asyncio.to_thread(self.snapshot, session_id)
                except NotFound:
                    self._clients.pop(client_id, None)
                    continue
                if queue.full():
                    queue.get_nowait()
                    self._dropped += 1
                queue.put_nowait(snapshot)
            await asyncio.sleep(.05)

    async def subscribe(self, session_id, generation):
        # Session locks can wait on bounded source inspection or recording I/O.
        # Snapshot off the event loop; subscriber accounting stays on the loop.
        if len(self._clients) >= self.max_clients:
            raise BusyError("Live spectator connection limit reached.")
        client_id, queue = uuid.uuid4().hex, asyncio.Queue(maxsize=1)
        self._clients[client_id] = (session_id, queue)
        try:
            await asyncio.to_thread(self.entry, session_id, generation)
            snapshot = await asyncio.to_thread(self.snapshot, session_id)
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(snapshot)
        except BaseException:
            self.unsubscribe(client_id)
            raise
        return client_id, queue

    def unsubscribe(self, client_id):
        self._clients.pop(client_id, None)

    def stream_stats(self):
        return dict(clients=len(self._clients), max_queue=max((q.qsize() for _, q in self._clients.values()), default=0),
                    dropped=self._dropped)
