"""Explicitly started session: one continuous reader and one supervised worker.

No constructor or status read starts capture or inference. The session owns the
fixed-step flight clock; callers must explicitly renew the owner lease.
"""
from copy import deepcopy
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import time
import uuid

from .accounting import LiveLedger, LiveOwnership
from .capture import Capture
from .child import command
from .contracts import NeuralSample, SessionConfig, SessionStatus
from .encoding import encode_frame
from .flight import FlightAuthority, decode, neutralize
from .neural import SessionSnapshot, StepRequest, StepResult, receive_packet, send_packet
from .worker import REPOSITORY, model_files

TERMINAL = {"stopped", "source_lost", "failed", "limit_reached"}


class NeuralSession:
    def __init__(self, config: SessionConfig, *, purpose: str, repository_root=REPOSITORY,
                 files=None, expected_device=None, monitor=None, capture_factory=Capture,
                 worker_command=None, recording_store=None, source=None, backend="cpu"):
        self.config = SessionConfig.model_validate(config.model_dump())
        if self.config.recording and (recording_store is None or source is None):
            raise ValueError("recording requires a private store and explicit source metadata")
        self._recording_store, self._recording_source = recording_store, source
        self._recorder = None
        self._recording_state = "off"
        if purpose not in ("automated", "human", "fixture"):
            raise ValueError("explicit execution purpose required")
        self.root = Path(repository_root).resolve()
        self.files = files or model_files()
        if purpose != "fixture" and (self.root != REPOSITORY or worker_command is not None):
            raise ValueError("real execution requires fixed accounting and model worker")
        if purpose == "fixture" and not self.files.get("allow_fixture", False):
            raise ValueError("fixture execution requires explicitly synthetic model files")
        if self.config.source_id == "fixture-pattern":
            if self.config.evidence_kind != "fixture":
                raise ValueError("synthetic source must be labeled fixture")
        elif expected_device is None or self.config.evidence_kind != "real":
            raise ValueError("real session requires operator-confirmed source identity")
        if backend not in {"cpu", "cuda"}:
            raise ValueError("unknown neural backend")
        self.backend = backend
        self.purpose = purpose
        self.session_id, self.generation = uuid.uuid4().hex, 1
        self.capture = capture_factory(source_id=config.source_id, session_id=self.session_id,
                                       generation=self.generation, duration_s=config.duration_seconds,
                                       inactivity_s=config.source_deadline_ms / 1000,
                                       expected_device=expected_device, monitor=monitor,
                                       verified=config.source_id != "fixture-pattern")
        self._worker_command = worker_command
        self._lock = threading.RLock()
        self._cleanup_lock = threading.Lock()
        self._io_active = threading.Event()
        self._stop = threading.Event()
        self._done = threading.Event()
        self._thread = self._child = self._channel = self._ownership = None
        self._state, self._reason = "idle", None
        self._started = self._lease = self._ready_time = None
        self._pending = self._inferred = self._result = None
        self._attempted = self._completed = self._rejected = 0
        self._last_sequence = -1
        self._step_started = self._last_step_ms = None
        self._provenance = None
        self._latest_receipt = self._ended = None
        self._flight = FlightAuthority(self.session_id, self.generation, self.config.evidence_kind,
                                       origin_ms=time.monotonic()*1000)

    def start(self):
        with self._lock:
            if self._state != "idle":
                return self  # A terminal session cannot resume; new Start needs a new ID.
            ownership = LiveOwnership(self.root).acquire()
            self._ownership = ownership
            self._started = self._lease = time.monotonic()
            self._flight = FlightAuthority(self.session_id, self.generation, self.config.evidence_kind,
                                           origin_ms=self._started*1000)
            self._state = "starting"
            self._thread = threading.Thread(target=self._run, name="live-session", daemon=True)
            try:
                if self.config.recording:
                    self._recorder = self._recording_store.reserve(self.config, self._recording_source,
                                                                  self.session_id, self.generation)
                    self._recording_state = "partial"
                    if time.monotonic()-self._lease >= self.config.lease_ms/1000:
                        self._recorder.abort()
                        self._recording_state = "aborted"
                        self._state, self._reason = "stopped", "Control lease expired during recording setup."
                        ownership.close()
                        self._done.set()
                        return self
                self._thread.start()
                if self.config.recording:
                    threading.Thread(target=self._recording_watchdog, daemon=True,
                                     name="live-recording-watchdog").start()
            except Exception:
                if self._recorder:
                    self._recorder.abort()
                    self._recording_state = "aborted"
                ownership.close()
                self._state = "failed"
                self._done.set()
                raise
        return self

    def renew_lease(self):
        with self._lock:
            if self._state in ("starting", "running"):
                # An already expired lease can never be revived by a late heartbeat.
                if time.monotonic() - self._lease >= self.config.lease_ms / 1000:
                    self._finish("stopped", "Control lease expired; explicit Start required.")
                    return False
                self._lease = time.monotonic()
                return True
            return False

    @property
    def lease_remaining_ms(self):
        with self._lock:
            return (max(0., self.config.lease_ms-(time.monotonic()-self._lease)*1000)
                    if self._state in {"starting", "running"} else 0.)

    @property
    def recording_id(self):
        return self._recorder.recording_id if self._recorder else None

    @property
    def recording_state(self):
        return self._recording_state

    def _finish(self, state, reason):
        with self._lock:
            self._flight.stop()
            if self._state not in TERMINAL:
                self._state, self._reason = state, reason
                self._ended = time.monotonic()
            self._stop.set()

    def stop(self):
        self._stop.set()
        with self._lock:
            self._flight.stop()
            if self._state == "idle":
                self._state, self._reason = "stopped", "Stopped before Start."
                self._done.set()
            elif self._state not in TERMINAL:
                self._state, self._reason = "stopping", "Operator stopped session."
                self._ended = time.monotonic()
            self._stop.set()
        if self._thread is not threading.current_thread():
            self._done.wait(self.config.stop_grace_ms / 1000)
        return self.snapshot()

    def _record_io(self, operation):
        """Persist outside the session lock; watchdog owns stalled-I/O shutdown.

        Called only by the coordinator while holding its lock. A stalled private
        filesystem may retain a writer thread, but cannot retain capture/model
        resources or publish a falsely completed interrupted session.
        """
        self._io_active.set()
        self._lock.release()
        try:
            return operation()
        finally:
            self._lock.acquire()
            self._io_active.clear()

    def _recording_watchdog(self):
        while not self._done.wait(.02):
            if not self._io_active.is_set():
                continue
            with self._lock:
                if self._done.is_set() or not self._io_active.is_set():
                    continue
                try:
                    expired = self._deadlines(time.monotonic())
                except (OSError, RuntimeError):
                    expired = ("failed", "Ownership lost during recording.")
                if not expired and not self._stop.is_set():
                    continue
                if expired:
                    self._finish(*expired)
                self._recording_state = "aborted"
            self._cleanup()
            return

    def wait(self, timeout=None):
        return self._done.wait(timeout)

    @property
    def provenance(self):
        with self._lock:
            return deepcopy(self._provenance)

    def _launch(self):
        parent, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
        self._channel = parent
        try:
            arguments = (self._worker_command or [sys.executable, "-m", "flytrap.live.worker"]) + [str(child.fileno())]
            self._child = subprocess.Popen(command(arguments), cwd=REPOSITORY,
                                           pass_fds=(*self._ownership.filenos, child.fileno()),
                                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                           stderr=subprocess.DEVNULL,
                                           env={**os.environ, "OMP_NUM_THREADS": "1",
                                                "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"})
            parent.settimeout(.05)
            send_packet(parent, {"config": self.config.model_dump(mode="json"), "purpose": self.purpose,
                                 "backend": self.backend,
                                 "repository_root": str(self.root), "session_id": self.session_id,
                                 "generation": self.generation, "lock_fds": self._ownership.filenos,
                                 "files": {k: str(v) if isinstance(v, Path) else v for k, v in self.files.items()}})
            parent.setblocking(False)
        finally:
            child.close()

    def _deadlines(self, now):
        self._ownership.require_active(self.root)
        if now - self._lease >= self.config.lease_ms / 1000:
            return "stopped", "Control lease expired; explicit Start required."
        if now - self._started >= self.config.duration_seconds:
            return "limit_reached", "Session duration limit reached."
        if self._ready_time is None and now - self._started >= self.config.startup_deadline_ms / 1000:
            return "failed", "Neural startup deadline exceeded."
        if self._pending and now - self._step_started >= self.config.step_deadline_ms / 1000:
            return "failed", "Neural step deadline exceeded; attempt remains counted."
        status = self.capture.status()
        if status.state in TERMINAL:
            return ("limit_reached" if status.state == "limit_reached" else "source_lost"), "Source stopped or lost."
        if not self._producer_active(status):
            return "source_lost", "Source producer status lost."
        latest = self.capture.slot.latest()
        if latest:
            self._latest_receipt = latest.identity.receipt_monotonic_ms
        receipt = self._latest_receipt if self._latest_receipt is not None else self._started * 1000
        if now * 1000 - receipt >= self.config.source_deadline_ms:
            return "source_lost", "Source receipt deadline exceeded."
        return None

    def _producer_active(self, status):
        return status.producer == "active" or (self.config.source_id == "fixture-pattern"
                and self.config.evidence_kind == "fixture" and status.producer == "synthetic")

    def _receive(self, payload):
        kind = payload.get("kind")
        with self._lock:
            if self._stop.is_set():
                return
            if kind == "ready" and self._ready_time is None:
                self._provenance = payload["provenance"]
                if self.backend == "cuda" and self._provenance.get("neural_execution", {}).get("backend") != "cuda-torch-csr-v1":
                    raise ValueError("CUDA worker returned an incorrect execution identity")
                if self._recorder:
                    from .recording import provenance_from_worker
                    backend = "synthetic-fixture-v1"
                    if self.config.evidence_kind == "real":
                        backend = subprocess.check_output(["ffmpeg", "-version"], text=True,
                                                          timeout=2).splitlines()[0][:128]
                    initial = self._flight.trace().initial
                    provenance = provenance_from_worker(self._provenance, backend_version=backend)
                    self._recorder = self._record_io(lambda: self._recorder.initialize(provenance, initial))
                    if self._stop.is_set():
                        return
                self._ready_time = time.monotonic()
                self._state = "running"
                return
            if kind == "failed":
                self._finish("failed", "Neural worker failed; attempts remain counted.")
                return
            if kind == "attempt" and self._pending is not None and payload.get("step_index") == self._completed:
                if self._attempted != self._completed:
                    raise ValueError("duplicate attempt notification")
                self._attempted += 1
                return
            result = StepResult.model_validate(payload)
            if self._pending is None or (result.session_id, result.generation, result.step_index) != (
                    self.session_id, self.generation, self._completed):
                raise ValueError("foreign or unexpected result")
            if self._attempted != self._completed + 1:
                raise ValueError("result without prior attempt")
            now = time.monotonic()
            if result.completed_monotonic_ms > now * 1000:
                raise ValueError("result timestamp is in the future")
            self._last_step_ms = (now - self._step_started) * 1000
            self._result = result
            self._inferred = NeuralSample(schema_version="obs-neural-1",
                response_id=f"{self.session_id}-{self._completed}", frame=self._pending.frame,
                observation_u8=list(self._pending.u8), encoder_id=self._pending.encoder_id,
                model_id=self._provenance["model_id"], step_index=self._completed,
                completed_monotonic_ms=result.completed_monotonic_ms, neural_ms=20.,
                neural_state_mode="windowed_reset", motor_rates_hz=result.motor_rates_hz,
                raw_action=result.raw_action)
            if self._recorder:
                self._record_io(lambda: self._recorder.append_sample(self._inferred, result))
                if self._stop.is_set():
                    return
            self._completed += 1
            # Recording fsync is allowed to delay work, never to extend freshness
            # or ownership. Recheck after persistence before installing controls.
            now = time.monotonic()
            expired = self._deadlines(now) if self._recorder else None
            if expired:
                self._pending = None
                self._finish(*expired)
                return
            if now * 1000 - self._pending.frame.receipt_monotonic_ms >= self.config.response_max_age_ms:
                self._rejected += 1
            else:
                self._flight.apply(decode(self._inferred.motor_rates_hz,
                    response_id=self._inferred.response_id, session_id=self.session_id,
                    generation=self.generation, evidence_kind=self.config.evidence_kind,
                    receipt_ms=self._pending.frame.receipt_monotonic_ms,
                    completed_ms=result.completed_monotonic_ms, now_ms=now*1000,
                    max_age_ms=float(self.config.response_max_age_ms)), now_ms=now*1000)
            self._pending = None
            if self._completed >= self.config.max_model_calls:
                self._finish("limit_reached", "Session model-call limit reached.")

    def _schedule(self):
        with self._lock:
            if self._stop.is_set() or self._ready_time is None or self._pending is not None:
                return
            frame = self.capture.slot.take()
            if frame is None:
                return
            identity = frame.identity
            if (identity.source_id, identity.session_id, identity.generation, identity.evidence_kind) != (
                    self.config.source_id, self.session_id, self.generation, self.config.evidence_kind):
                raise ValueError("foreign source frame")
            if identity.sequence <= self._last_sequence:
                raise ValueError("source sequence did not advance")
            now = time.monotonic()
            age = now * 1000 - identity.receipt_monotonic_ms
            if age < 0 or age >= min(self.config.source_deadline_ms, self.config.response_max_age_ms):
                return
            self._pending = encode_frame(frame)
            self._latest_receipt = identity.receipt_monotonic_ms
            self._last_sequence = identity.sequence
            self._step_started = now
            request = StepRequest(session_id=self.session_id, generation=self.generation,
                                  step_index=self._completed, observation_u8=list(self._pending.u8))
            if self._recorder:
                pending = self._pending
                self._record_io(lambda: self._recorder.append_input(pending.frame, list(pending.u8), self._completed))
                if self._stop.is_set():
                    return
                now = time.monotonic()
                expired = self._deadlines(now)
                if expired:
                    self._finish(*expired)
                    return
                if now * 1000 - identity.receipt_monotonic_ms >= self.config.response_max_age_ms:
                    self._finish("failed", "Recording delayed the input beyond its freshness deadline.")
                    return
                self._step_started = now
            send_packet(self._channel, request.model_dump(mode="json"))

    def _run(self):
        try:
            if not self._stop.is_set():
                self.capture.start()
            if not self._stop.is_set():
                self._launch()
            while not self._stop.is_set():
                expired = self._deadlines(time.monotonic())
                if expired:
                    self._finish(*expired)
                    break
                with self._lock:
                    self._flight.advance_to(time.monotonic()*1000)
                try:
                    payload = receive_packet(self._channel)
                except BlockingIOError:
                    payload = None
                if payload is not None:
                    self._receive(payload)
                if self._child.poll() is not None and not self._stop.is_set():
                    self._finish("failed", "Neural worker exited; explicit Start required.")
                    break
                self._schedule()
                self._stop.wait(.005)
        except Exception:
            self._finish("failed", "Session worker, source or accounting failed; explicit Start required.")
        finally:
            self._cleanup()
            self._finalize_recording()

    def _cleanup(self):
        with self._cleanup_lock:
            if self._done.is_set():
                return
            self._cleanup_owned()

    def _cleanup_owned(self):
        deadline = time.monotonic() + self.config.stop_grace_ms / 1000
        capture_stop = threading.Thread(target=self.capture.stop, daemon=True)
        capture_stop.start()
        child = self._child
        if child is not None and child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=min(.25, max(.001, deadline - time.monotonic())))
            except subprocess.TimeoutExpired:
                child.kill()
        if child is not None:
            try:
                child.wait(timeout=max(.001, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                self._state, self._reason = "failed", "Neural process cleanup deadline exceeded."
                # Keep the shared lock until the killed child is actually reaped.
                child.wait()
        if self._channel is not None:
            self._channel.close()
        ledger = LiveLedger.session(self.root, self.session_id, cap=self.config.max_model_calls,
                                    mode="human" if self.purpose == "human" else "automated")
        if ledger.path.exists() or ledger.checkpoint.exists():
            try:
                self._attempted = ledger.attempted
            except (ValueError, OSError, RuntimeError):
                self._attempted = self.config.max_model_calls
                self._state, self._reason = "failed", "Accounting unavailable; displayed attempts conservatively capped."
        capture_stop.join(max(0, deadline - time.monotonic()))
        if capture_stop.is_alive():
            self._state, self._reason = "failed", "Capture cleanup deadline exceeded."
            # Stop returns at its deadline. Keep exclusion while background cleanup
            # remains unresolved; a new owner must never overlap this reader.
            capture_stop.join()
        if not self.capture.wait_closed(max(0., deadline - time.monotonic())):
            self._state, self._reason = "failed", "Capture resources remain active after cleanup deadline."
            while not self.capture.wait_closed(.25):
                pass  # Retain ownership; no model is left running or rescheduled.
        if self._ownership is not None:
            self._ownership.close()
        with self._lock:
            self._flight.stop()
            if self._state not in TERMINAL:
                self._state = "stopped"
            self._recording_can_complete = (self._state in {"stopped", "limit_reached"}
                and self._ready_time is not None and self._pending is None
                and self._recording_state != "aborted")
            self._pending = None
            self._done.set()

    def _finalize_recording(self):
        # Capture/model resources have been reaped. Final fsync cannot delay Stop
        # or snapshots; only successful publication changes partial to complete.
        if self._recorder:
            try:
                if self._recording_can_complete:
                    self._recorder.finish(self._flight.trace(), self._flight.current)
                    self._recording_state = "complete"
                else:
                    self._recorder.abort()
                    self._recording_state = "aborted"
            except (OSError, ValueError, AttributeError):
                self._recorder.abort()
                self._recording_state = "aborted"
                self._state, self._reason = "failed", "Recording failed; partial artifacts remain private."

    def snapshot(self):
        with self._lock:
            now = time.monotonic()
            captured = self.capture.status()
            frame = self.capture.slot.latest()
            if frame is not None:
                self._latest_receipt = frame.identity.receipt_monotonic_ms
            age = None if self._latest_receipt is None else max(0., now * 1000 - self._latest_receipt)
            sample = self._inferred
            if (self._state != "running" or self._stop.is_set() or sample is None
                    or now - self._lease >= self.config.lease_ms / 1000
                    or now * 1000 - sample.frame.receipt_monotonic_ms >= self.config.response_max_age_ms
                    or captured.state != "previewing" or not self._producer_active(captured)
                    or age is None or age >= self.config.source_deadline_ms):
                sample = None
            # Reads never integrate elapsed time. They still neutralize immediately
            # if safety validity is lost before the coordinator next polls.
            flight = self._flight.current.snapshot
            if sample is None and not flight.neutral:
                flight = neutralize(self._flight.current).snapshot
            status = SessionStatus(schema_version="obs-session-status-1", session_id=self.session_id,
                generation=self.generation, evidence_kind=self.config.evidence_kind, state=self._state,
                reason=self._reason, attempted_calls=self._attempted, accepted_frames=captured.accepted_frames,
                overwritten_frames=captured.overwritten_frames, content_unchanged_ms=captured.content_unchanged_ms,
                producer_health="active" if self._producer_active(captured) else captured.producer,
                last_frame_sequence=None if self._last_sequence < 0 else self._last_sequence,
                last_response_id=None if sample is None else sample.response_id)
            elapsed = 0 if self._ready_time is None else (self._ended or now) - self._ready_time
            return SessionSnapshot(status, deepcopy(sample), deepcopy(self._inferred), deepcopy(self._result),
                                   self._pending is not None, self._completed, self._rejected,
                                   self._completed * 20., self._completed / elapsed if elapsed > 0 else 0.,
                                   self._last_step_ms, age, self.purpose if self.purpose == "fixture" else "real",
                                   deepcopy(flight))

    @property
    def flight_events(self):
        """Bounded control applications in memory; no recording is enabled."""
        with self._lock:
            return deepcopy(self._flight.events)

    @property
    def flight_trace(self):
        """Complete replay inputs, held only in memory while recording is off."""
        with self._lock:
            return deepcopy(self._flight.trace())
