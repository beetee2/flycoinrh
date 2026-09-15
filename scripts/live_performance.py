"""Bounded OBS06 synthetic lifecycle measurements; never opens hardware/model.

Run with ``.venv/bin/python -m scripts.live_performance --output DIR``.
The real HTTP service, capture coordinator, IPC, flight clock and cleanup run
with a deliberately delayed synthetic worker. Timings are not neural latency.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import socket
import statistics
import subprocess
import sys
import time

from flytrap.live.accounting import LiveLedger, LiveOwnership
from flytrap.live.api import create_live_app
from flytrap.live.contracts import SourceCapability
from flytrap.live.encoding import RGBFrame, encode_frame
from flytrap.live.fixture import fixture_frame
from flytrap.live.neural import receive_packet, send_packet
from flytrap.live.service import LiveService
from flytrap.live.session import NeuralSession
from tests.live.session_fault_worker import result
from tests.live.test_session_api import owner, path, serve, start, start_body


def worker(fd):
    """Alternate fresh/late replies under a fixed schedule, without inference."""
    with socket.socket(fileno=fd) as channel:
        init = receive_packet(channel)
        root = Path(init["repository_root"])
        ownership = LiveOwnership.from_inherited(root, init["lock_fds"])
        ledger = LiveLedger.session(root, init["session_id"], mode="automated", cap=32)
        send_packet(channel, {"kind": "ready", "provenance": {"model_id": "synthetic-perf-only"}})
        try:
            for step in range(32):
                request = receive_packet(channel)
                ledger.record_attempt(session_id=init["session_id"], seed=init["config"]["seed"],
                                      step=step, ownership=ownership)
                send_packet(channel, {"kind": "attempt", "step_index": step})
                time.sleep(.06 if step % 2 == 0 else .22)
                send_packet(channel, result(init, request))
            receive_packet(channel)
        except (EOFError, BrokenPipeError, ConnectionResetError):
            pass


def summary(values):
    ordered = sorted(values)
    return {"count": len(values), "min": min(values), "median": statistics.median(values),
            "p95": ordered[min(len(values) - 1, int(len(values) * .95))], "max": max(values)}


def rss_kib(pid):
    try:
        for line in Path(f"/proc/{pid}/status").read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    except FileNotFoundError:
        pass
    return None


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    isolated_root = output / "fixture-root"
    source = SourceCapability(schema_version="obs-source-1", source_id="fixture-pattern",
        evidence_kind="fixture", name="Deterministic generated performance fixture", driver=None,
        backend="synthetic", capabilities=None, formats=None, metadata_state="available",
        producer_detection="synthetic")
    sessions = []

    def factory(config, **kwargs):
        session = NeuralSession(config, purpose="fixture", repository_root=isolated_root,
            files={"allow_fixture": True}, worker_command=[sys.executable, "-m",
                "scripts.live_performance", "worker"])
        sessions.append(session)
        return session

    service = LiveService(repository_root=isolated_root, session_factory=factory,
                          source_provider=lambda: [source], execution_purpose="automated")
    metrics = {"schema_version": "obs06-performance-1", "kind": "synthetic-no-model",
        "full_model_calls": 0, "hardware_access": False, "recording": False,
        "command": sys.argv, "python": platform.python_version(), "platform": platform.platform(),
        "revision": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "bounds": {"max_synthetic_attempts": 32, "loop_deadline_seconds": 12,
                   "worker_delays_seconds": [.06, .22], "response_max_age_ms": 120},
        "source_age_ms": None,
        "source_age_note": "Generated source only; OBS producer/capture timestamp is unknown.",
        "real_model_load_step_latency": "See separate real-model gate evidence.",
        "render_fps": "See separate browser evidence."}
    receipts, health, status_times, resident, child_resident, samples = [], [], [], [], [], {}
    began = time.monotonic()
    with serve(create_live_app(dist=output / "missing-dist", service=service)) as (client, _):
        client.headers.update({"Origin": str(client.base_url).rstrip("/"),
            "X-Live-CSRF": client.get("/api/live/control").json()["csrf_token"]})
        body = start_body(duration_seconds=12, max_model_calls=32, response_max_age_ms=120)
        snapshot = start(client, body)
        session = sessions[0]
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            tick = time.monotonic()
            assert client.get("/health/live").status_code == 200
            health.append((time.monotonic() - tick) * 1000)
            tick = time.monotonic()
            assert client.get(path(snapshot)).status_code == 200
            status_times.append((time.monotonic() - tick) * 1000)
            state = session.snapshot()
            if state.source_receipt_age_ms is not None:
                receipts.append(state.source_receipt_age_ms)
            if state.last_inferred is not None:
                sample = state.last_inferred
                samples[sample.step_index] = {"step": sample.step_index,
                    "capture_sequence": sample.frame.sequence,
                    "source_sequence": sample.frame.source_sequence,
                    "receipt_to_completed_ms": sample.completed_monotonic_ms - sample.frame.receipt_monotonic_ms,
                    "worker_roundtrip_ms": state.last_step_wall_ms}
            resident.append(rss_kib(os.getpid()))
            if session._child is not None:
                value = rss_kib(session._child.pid)
                if value is not None:
                    child_resident.append(value)
            if session.wait(0):
                break
            renewal = client.post(path(snapshot, "/renew"), json=owner(body))
            # The final response can end the session between snapshot and renewal.
            assert renewal.status_code == 200 or (
                renewal.status_code == 409 and session.snapshot().status.state == "limit_reached")
            time.sleep(.02)
        stop_began = time.monotonic()
        assert client.post(path(snapshot, "/stop"), json=owner(body)).status_code == 200
        metrics["stop_request_ms"] = (time.monotonic() - stop_began) * 1000
        assert session.wait(2)
        state = session.snapshot()
        assert state.completed_calls == state.status.attempted_calls == 32
        assert state.rejected_results >= 16
        assert len(samples) == 32
        assert session.capture.slot.overwritten > 50
        assert session._child.poll() is not None
        assert session.capture.wait_closed(1)
        assert state.flight.neutral and state.sample is None
        with LiveOwnership(isolated_root):
            pass
        metrics.update({"elapsed_seconds": time.monotonic() - began,
            "completed_synthetic_responses": state.completed_calls, "rejected_stale_results": state.rejected_results,
            "capture_accepted": session.capture.slot.accepted,
            "capture_overwritten": session.capture.slot.overwritten,
            "receipt_age_ms": summary(receipts), "health_http_ms": summary(health),
            "session_http_ms": summary(status_times), "parent_rss_kib": summary(resident),
            "synthetic_worker_rss_kib": summary(child_resident), "samples": list(samples.values()),
            "cleanup": {"child_reaped": True, "capture_closed": True, "lock_reacquired": True,
                        "terminal_neutral": True}, "terminal_state": state.status.state})
    # Isolate encoder costs from capture, HTTP and model delays; save no pixels.
    encoding = {}
    for width, height in ((320, 180), (1280, 720)):
        small = fixture_frame(0, "encoding-perf", 1)
        frame = RGBFrame(small.identity.model_copy(update={"width": width, "height": height}),
                         bytes((34, 89, 144)) * (width * height))
        times = []
        for _ in range(100):
            tick = time.perf_counter()
            encode_frame(frame)
            times.append((time.perf_counter() - tick) * 1000)
        encoding[f"{width}x{height}_ms"] = summary(times)
    metrics["encoder_only"] = encoding
    metrics["result"] = "PASS"
    metrics["command_exit"] = 0
    (output / "result.json").write_text(json.dumps(metrics, indent=2) + "\n")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "worker":
        worker(int(sys.argv[2]))
    else:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--output", type=Path, required=True)
        run(parser.parse_args().output.resolve())
