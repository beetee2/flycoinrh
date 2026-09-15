"""Continuous frame draining with a capacity-one slot and bounded ownership.

No constructor starts capture. Call start only following explicit selection and
preview/Start consent. No inference or image persistence is performed here.
"""
from dataclasses import dataclass
import hashlib
import os
import selectors
import subprocess
import threading
import time

from .contracts import FrameIdentity
from .device import DeviceConfig, SourceError, inspect_selected, selected_path
from .encoding import RGBFrame


@dataclass(frozen=True)
class CaptureStatus:
    state: str
    reason: str | None
    accepted_frames: int
    overwritten_frames: int
    rejected_frames: int
    producer: str
    verified_live: bool
    content_unchanged_ms: float


class LatestFrameSlot:
    def __init__(self, source_id: str, session_id: str, generation: int):
        self.identity = source_id, session_id, generation
        self._condition = threading.Condition()
        self._frame = None
        self._last_sequence = -1
        self._last_receipt = -1
        self.accepted = self.overwritten = self.rejected = 0
        self.closed = False

    def put(self, frame: RGBFrame) -> bool:
        identity = frame.identity
        with self._condition:
            if (self.closed or (identity.source_id, identity.session_id, identity.generation) != self.identity
                    or identity.sequence <= self._last_sequence
                    or identity.receipt_monotonic_ms < self._last_receipt):
                self.rejected += 1
                return False
            self.overwritten += int(self._frame is not None)
            self.accepted += 1
            self._last_sequence = identity.sequence
            self._last_receipt = identity.receipt_monotonic_ms
            self._frame = frame
            self._condition.notify_all()
            return True

    def latest(self):
        with self._condition:
            return self._frame

    def take(self, timeout: float = 0):
        if not 0 <= timeout <= 2:
            raise ValueError("Frame wait must be bounded to two seconds.")
        with self._condition:
            self._condition.wait_for(lambda: self._frame is not None or self.closed, timeout)
            frame, self._frame = self._frame, None
            return frame

    def close(self):
        with self._condition:
            self.closed = True
            self._frame = None
            self._condition.notify_all()


class PPMReader:
    """Strict FFmpeg P6 frame parser. Headers retain resolution across reinit.

    Parser storage is at most one bounded frame plus a read chunk. PPM carries no
    trusted source timing; source sequence/timestamp stay null for real capture.
    """
    def __init__(self, width: int, height: int):
        if not 1 <= width <= 8192 or not 1 <= height <= 8192 or width * height * 3 > 32 * 1024**2:
            raise SourceError("Malformed or oversized frame dimensions.")
        self.width, self.height = width, height
        self.buffer = bytearray()
        self.header_done = False

    def feed(self, chunk: bytes):
        if len(chunk) > 65536:
            raise SourceError("Capture read chunk exceeds its bound.")
        self.buffer.extend(chunk)
        frames = []
        while True:
            if not self.header_done:
                # FFmpeg ppm encoder writes exactly P6\nW H\n255\n.
                end = self.buffer.find(b"\n", self.buffer.find(b"\n", self.buffer.find(b"\n") + 1) + 1)
                if self.buffer.count(b"\n") < 3:
                    if len(self.buffer) > 64:
                        raise SourceError("Malformed capture frame header.")
                    break
                header = bytes(self.buffer[:end + 1])
                if header != f"P6\n{self.width} {self.height}\n255\n".encode():
                    raise SourceError("Capture format changed or frame header is invalid; start a new preview/session.")
                del self.buffer[:end + 1]
                self.header_done = True
            size = self.width * self.height * 3
            if len(self.buffer) < size:
                break
            frames.append(bytes(self.buffer[:size]))
            del self.buffer[:size]
            self.header_done = False
        return frames

    def eof(self):
        if self.buffer or self.header_done:
            raise SourceError("Capture ended with a partial frame.")


def ffmpeg_arguments(config: DeviceConfig) -> list[str]:
    config.validate()
    path = selected_path(config.source_id)
    current = path.stat()
    if (current.st_rdev, current.st_ino) != (config.device_number, config.inode):
        raise SourceError("Selected device identity changed; select it again.")
    pixel_format = {"RGB3": "rgb24", "BGR3": "bgr24", "YUYV": "yuyv422", "NV12": "nv12"}[config.fourcc]
    arguments = ["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-nostats",
                 "-thread_queue_size", "1", "-fflags", "nobuffer", "-analyzeduration", "0",
                 "-probesize", "32", "-f", "v4l2", "-input_format", pixel_format,
                 "-video_size", f"{config.width}x{config.height}", "-framerate",
                 f"{config.fps_denominator}/{config.fps_numerator}", "-i", str(path)]
    if config.fourcc in ("YUYV", "NV12"):
        arguments += ["-vf", f"scale=iw:ih:in_color_matrix=bt601:in_range={config.color_range}:out_range=full"]
    return arguments + output_arguments()


def output_arguments():
    return ["-map", "0:v:0", "-an", "-sn", "-dn", "-threads", "1", "-filter_threads", "1",
            "-fps_mode", "passthrough", "-c:v", "ppm", "-pix_fmt", "rgb24", "-f", "image2pipe",
            "-flush_packets", "1", "pipe:1"]


class Capture:
    def __init__(self, *, source_id: str, session_id: str, generation: int,
                 duration_s: float = 30, inactivity_s: float = 2, monitor=None, verified: bool = False,
                 expected_device: DeviceConfig | None = None):
        # Validate identities even before starting a subprocess.
        FrameIdentity(schema_version="obs-frame-1", source_id=source_id, session_id=session_id,
                      generation=generation, sequence=0, evidence_kind="fixture" if source_id == "fixture-pattern" else "real",
                      width=1, height=1, pixel_format="RGB24", receipt_monotonic_ms=0.,
                      source_timestamp_ms=None, source_sequence=None, source_clock="unknown")
        if not 0 < duration_s <= 120 or not 0 < inactivity_s <= 2:
            raise ValueError("Capture duration/freshness exceeds live bounds.")
        self.slot = LatestFrameSlot(source_id, session_id, generation)
        self.duration_s, self.inactivity_s = duration_s, inactivity_s
        self.monitor, self.verified = monitor, verified
        self.expected_device = expected_device
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._lifecycle = threading.Lock()
        self._state, self._reason = "idle", None
        self._thread = self._watcher = self._child = None
        self._receipt = self._changed = None
        self._digest = None
        self._diagnostics = bytearray()
        self._producer = "unknown"
        self._producer_checked = None
        self._config = None

    def start(self):
        with self._lifecycle:
            return self._start()

    def _start(self):
        with self._lock:
            if self._state != "idle":
                raise SourceError("Capture objects are single-use; create a new generation for Start.")
            self._state = "starting"
        try:
            if self.slot.identity[0] == "fixture-pattern":
                self._producer = "synthetic"
                self._thread = threading.Thread(target=self._fixture_loop, daemon=True)
            else:
                self._config = inspect_selected(self.slot.identity[0])
                if self.expected_device is not None and self._config != self.expected_device:
                    raise SourceError("Selected device differs from the operator-confirmed identity/configuration.")
                if self.verified and self.monitor is None and self._config.producer_detection != "driver":
                    raise SourceError("Verified OBS capture requires reliable driver status or an authenticated local monitor.")
                if self._config.producer_detection == "driver":
                    self._producer, self._producer_checked = "active", time.monotonic()
                if self._stop.is_set():
                    self._finish("stopped", "Operator stopped during selected-device inspection.")
                    return self
                arguments = ffmpeg_arguments(self._config)
                from .child import command
                self._child = subprocess.Popen(command(arguments), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                               stderr=subprocess.PIPE, bufsize=0, shell=False)
                self._thread = threading.Thread(target=self._pipe_loop, daemon=True)
                self._watcher = threading.Thread(target=self._watch_loop, daemon=True)
            self._started = time.monotonic()
            self._state = "previewing"
            self._thread.start()
            if self._watcher:
                self._watcher.start()
        except Exception:
            self._finish("failed", "Selected source could not start.")
            self._reap()
            raise
        return self

    def _finish(self, state, reason):
        with self._lock:
            if self._state not in ("stopped", "failed", "source_lost", "limit_reached"):
                self._state, self._reason = state, reason
            self._stop.set()
            self.slot.close()

    def _accept(self, rgb: bytes, width: int, height: int, *, fixture_sequence=None):
        now = time.monotonic()
        if self._stop.is_set() or now - self._started >= self.duration_s:
            return
        digest = hashlib.sha256(rgb).digest()
        with self._lock:
            if digest != self._digest:
                self._changed, self._digest = now, digest
            self._receipt = now
        source_id, session_id, generation = self.slot.identity
        frame = RGBFrame(FrameIdentity(
            schema_version="obs-frame-1", source_id=source_id, session_id=session_id, generation=generation,
            sequence=self.slot.accepted, evidence_kind="fixture" if fixture_sequence is not None else "real",
            width=width, height=height, pixel_format="RGB24", receipt_monotonic_ms=now * 1000,
            source_timestamp_ms=now * 1000 if fixture_sequence is not None else None,
            source_sequence=fixture_sequence, source_clock="local_monotonic" if fixture_sequence is not None else "unknown",
        ), rgb)
        self.slot.put(frame)

    def _fixture_loop(self):
        from .fixture import fixture_frame
        sequence = 0
        try:
            while not self._stop.is_set():
                if time.monotonic() - self._started >= self.duration_s:
                    self._finish("limit_reached", "Explicit preview/capture duration expired.")
                    break
                frame = fixture_frame(sequence, self.slot.identity[1], self.slot.identity[2])
                self._accept(frame.rgb, frame.identity.width, frame.identity.height, fixture_sequence=sequence)
                sequence += 1
                self._stop.wait(max(0, self._started + sequence / 30 - time.monotonic()))
        except Exception:
            self._finish("failed", "Synthetic source failed.")

    def _pipe_loop(self):
        parser = PPMReader(self._config.width, self._config.height)
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(self._child.stdout, selectors.EVENT_READ, "frame")
                selector.register(self._child.stderr, selectors.EVENT_READ, "diagnostic")
                while not self._stop.is_set():
                    now = time.monotonic()
                    if now - self._started >= self.duration_s:
                        self._finish("limit_reached", "Explicit preview/capture duration expired.")
                        break
                    if now - (self._receipt or self._started) >= self.inactivity_s:
                        self._finish("source_lost", "No complete source frame within the receipt deadline.")
                        break
                    for key, _ in selector.select(.025):
                        chunk = os.read(key.fileobj.fileno(), 65536)
                        if not chunk:
                            selector.unregister(key.fileobj)
                            if key.data == "frame":
                                parser.eof()
                                self._finish("source_lost", "Capture reached EOF.")
                                break
                        elif key.data == "diagnostic":
                            # Never expose arbitrary stderr to browsers or persist it.
                            self._diagnostics.extend(c for c in chunk if 32 <= c < 127 or c in (9, 10))
                            del self._diagnostics[:-4096]
                        else:
                            for rgb in parser.feed(chunk):
                                self._accept(rgb, parser.width, parser.height)
        except SourceError as exc:
            self._finish("source_lost", str(exc))
        except (OSError, ValueError):
            self._finish("failed", "Capture pipe failed.")
        finally:
            self._reap()

    def _watch_loop(self):
        while not self._stop.is_set():
            try:
                current = inspect_selected(self.slot.identity[0], timeout=.75)
                if current != self._config:
                    self._finish("source_lost", "Selected device identity or format changed; Start again.")
                    return
                if current.producer_detection == "driver":
                    self._producer, self._producer_checked = "active", time.monotonic()
            except SourceError:
                self._producer = "unknown"
                self._finish("source_lost", "Selected source became unavailable or its inspection timed out.")
                return
            if self.monitor is not None:
                status = self.monitor.poll()
                self._producer = status.state
                if status.state == "inactive" or (self.verified and status.state != "active"):
                    self._finish("source_lost", "OBS producer is inactive or its authenticated status is unavailable.")
                    return
            self._stop.wait(.25)

    def _reap(self):
        child = self._child
        if child is None:
            return
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=.5)
            except subprocess.TimeoutExpired:
                child.kill()
                try:
                    child.wait(timeout=.5)
                except subprocess.TimeoutExpired:
                    self._cleanup_failed("Capture process could not be reaped within its deadline.")
                    threading.Thread(target=child.wait, daemon=True).start()
        for pipe in (child.stdout, child.stderr):
            if pipe:
                pipe.close()

    def _cleanup_failed(self, reason):
        with self._lock:
            self._state, self._reason = "failed", reason
            self._stop.set()

    def stop(self):
        # Mark stop before waiting for an in-flight selected-device inspection.
        self._stop.set()
        with self._lifecycle:
            return self._stop_owned()

    def _stop_owned(self):
        self._finish("stopped", "Operator stopped capture.")
        for thread in (self._thread, self._watcher):
            if thread and thread is not threading.current_thread():
                thread.join(timeout=1.4)
                if thread.is_alive():
                    self._cleanup_failed("Capture worker did not stop within its cleanup deadline.")
        if self._thread is None and self._child is not None:
            self._reap()
        return self.status()

    def status(self):
        with self._lock:
            now = time.monotonic()
            producer = self.monitor.snapshot().state if self.monitor else self._producer
            if (self.monitor is None and self._producer_checked is not None
                    and now - self._producer_checked >= self.inactivity_s):
                producer = "unknown"
            fresh = self._receipt is not None and now - self._receipt < self.inactivity_s
            return CaptureStatus(self._state, self._reason, self.slot.accepted, self.slot.overwritten,
                                 self.slot.rejected, producer,
                                 self._state == "previewing" and fresh and producer == "active",
                                 0. if self._changed is None else (now - self._changed) * 1000)

    def wait_closed(self, timeout: float) -> bool:
        """Confirm actual owned-resource termination, including failed Stop paths."""
        if not 0 <= timeout <= 3:
            raise ValueError("capture cleanup wait must be bounded to three seconds")
        deadline = time.monotonic() + timeout
        for thread in (self._thread, self._watcher):
            if thread is not None and thread is not threading.current_thread():
                thread.join(max(0., deadline - time.monotonic()))
        if self._child is not None:
            try:
                self._child.wait(timeout=max(0., deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                return False
        return all(thread is None or not thread.is_alive() for thread in (self._thread, self._watcher))
