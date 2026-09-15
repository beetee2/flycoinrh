"""Bounded synthetic process/IPC fault helper; never imports or calls a model."""
import json
from pathlib import Path
import signal
import socket
import sys
import threading
import time

from flytrap.live.capture import CaptureStatus, LatestFrameSlot
from flytrap.live.contracts import FrameIdentity, SessionConfig
from flytrap.live.encoding import RGBFrame
from flytrap.live.neural import receive_packet, send_packet


class SyntheticCapture:
    """Small continuously refreshed RGB fixture with explicit stop ownership."""

    def __init__(self, *, source_id, session_id, generation, **kwargs):
        self.slot = LatestFrameSlot(source_id, session_id, generation)
        self.identity = dict(source_id=source_id, session_id=session_id, generation=generation)
        self.state = "idle"
        self.producer = "active"
        self._stop = threading.Event()
        self.thread = None

    def start(self):
        self.state = "previewing"
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        sequence = 0
        while not self._stop.is_set():
            frame = FrameIdentity(schema_version="obs-frame-1", **self.identity, sequence=sequence,
                evidence_kind="fixture", width=16, height=16, pixel_format="RGB24",
                receipt_monotonic_ms=time.monotonic() * 1000, source_timestamp_ms=None,
                source_sequence=sequence, source_clock="unknown")
            self.slot.put(RGBFrame(frame, bytes([sequence % 256]) * 768))
            sequence += 1
            self._stop.wait(.01)

    def status(self):
        return CaptureStatus(self.state, None, self.slot.accepted, self.slot.overwritten,
                             self.slot.rejected, self.producer, True, 0.)

    def stop(self):
        self._stop.set()
        if self.thread is not None:
            self.thread.join(1)
        self.slot.close()
        self.state = "stopped"

    def wait_closed(self, timeout):
        if self.thread is not None:
            self.thread.join(timeout)
        return self.thread is None or not self.thread.is_alive()


def config(**overrides):
    return SessionConfig(source_id="fixture-pattern", evidence_kind="fixture", seed=17,
                         **{"startup_deadline_ms": 2000, "lease_ms": 3000,
                            "step_deadline_ms": 1500, "stop_grace_ms": 1000,
                            **overrides})


def result(init, request):
    return dict(kind="result", session_id=init["session_id"], generation=init["generation"],
        step_index=request["step_index"], completed_monotonic_ms=time.monotonic() * 1000,
        output=dict(schema_version="1", dx=.25, dy=-.5, click=False, model_mode="fixture",
                    telemetry=dict(schema_version="1", sampled_neurons=15, spike_count=5, neural_ms=20.)),
        motor_rates_hz=dict(steer_L=0., steer_R=112.5, fwd_L=225., fwd_R=225., back=0., stop=0., click=0.),
        raw_action=dict(dx=22.5, dy=-45., click=False),
        statistics=dict(sampled_neurons=15, spike_count=5, firing=5, spikes_per_sec=250.,
                        mean_mv=-50., visual=3, motor=2), model_file_reads=0)


def worker(mode, fd):
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    with socket.socket(fileno=fd) as channel:
        init = receive_packet(channel)
        if mode == "startup_crash":
            return 23
        if mode == "startup_hang":
            time.sleep(10)
            return 0
        send_packet(channel, {"kind": "ready", "provenance": {"model_id": "synthetic-fault-worker"}})
        request = receive_packet(channel)
        if mode == "append_exit":
            from flytrap.live.accounting import LiveLedger, LiveOwnership

            owner = LiveOwnership.from_inherited(Path(init["repository_root"]), init["lock_fds"])
            ledger = LiveLedger.session(Path(init["repository_root"]), init["session_id"],
                                        mode="automated", cap=init["config"]["max_model_calls"])
            ledger.record_attempt(session_id=init["session_id"], seed=init["config"]["seed"],
                                  step=request["step_index"], ownership=owner)
            return 27
        send_packet(channel, {"kind": "attempt", "step_index": request["step_index"]})
        if mode == "step_crash":
            return 24
        if mode == "step_hang":
            time.sleep(10)
            return 0
        if mode == "stale":
            time.sleep(.2)
        payload = result(init, request)
        if mode == "foreign":
            payload["generation"] += 1
        if mode == "future":
            payload["completed_monotonic_ms"] += 10000
        send_packet(channel, payload)
        # The fault helper returns one result and then stays alive. The parent
        # must handle Stop/deadlines instead of relying on child exit cleanup.
        time.sleep(10)
    return 0


def parent_probe(root, files_path, ready_path):
    from flytrap.live.session import NeuralSession

    files = json.loads(Path(files_path).read_text())
    session = NeuralSession(config(), purpose="fixture", repository_root=Path(root), files=files,
        capture_factory=SyntheticCapture,
        worker_command=[sys.executable, "-m", "tests.live.session_fault_worker", "step_hang"])
    session.start()
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and session.snapshot().status.attempted_calls != 1:
        if session.wait(.01):
            return 25
        session.renew_lease()
    if session.snapshot().status.attempted_calls != 1:
        session.stop()
        return 26
    Path(ready_path).write_text(json.dumps({"worker_pid": session._child.pid}))
    while time.monotonic() < deadline:
        session.renew_lease()
        time.sleep(.02)
    session.stop()
    return 0


if __name__ == "__main__":
    if sys.argv[1] == "parent_probe":
        raise SystemExit(parent_probe(*sys.argv[2:]))
    raise SystemExit(worker(sys.argv[1], int(sys.argv[2])))
