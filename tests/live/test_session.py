"""Real subprocess and tiny, explicitly synthetic connectome integration."""
import time
import socket
from types import SimpleNamespace

import pytest

from flytrap.contracts import Observation
from flytrap.controllers.fly import FlyController
from flytrap.live.accounting import BusyError, LiveLedger, LiveOwnership
from flytrap.live.contracts import SessionConfig
from flytrap.live.session import NeuralSession
from flytrap.live.fixture import fixture_frame
from flytrap.live.neural import receive_packet
from tests.controllers import conftest as synthetic_fixtures

adapter_files = synthetic_fixtures.adapter_files
adapter_files_factory = synthetic_fixtures.adapter_files_factory


def collect(session, timeout=8):
    samples = {}
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        session.renew_lease()
        snapshot = session.snapshot()
        if snapshot.last_completed is not None:
            samples[snapshot.last_completed.step_index] = (snapshot.last_inferred, snapshot.last_completed)
        if session.wait(.005):
            snapshot = session.snapshot()
            if snapshot.last_completed is not None:
                samples[snapshot.last_completed.step_index] = (snapshot.last_inferred, snapshot.last_completed)
            return snapshot, samples
    session.stop()
    pytest.fail("session did not terminate within test bound")


def test_actual_persistent_fixture_worker_preserves_adapter_and_closes(adapter_files, tmp_path):
    config = SessionConfig(source_id="fixture-pattern", evidence_kind="fixture", seed=123,
                           duration_seconds=8, max_model_calls=3)
    session = NeuralSession(config, purpose="fixture", repository_root=tmp_path, files=adapter_files)
    assert session.snapshot().status.state == "idle" and session._child is None
    try:
        assert session.start().start() is session
        snapshot, samples = collect(session)
        assert snapshot.status.state == "limit_reached", snapshot
        assert snapshot.completed_calls == snapshot.status.attempted_calls == 3
        assert snapshot.sample is None and not snapshot.waiting_for_sample
        assert snapshot.neural_ms == 60.
        assert sorted(samples) == [0, 1, 2]
        assert session.provenance["model_loads"] == session.provenance["controller_resets"] == 1
        assert session.provenance["model"]["fixture"] is True
        original = FlyController(**adapter_files)
        original.reset(run_seed=123, checkpoint=original.checkpoint)
        sequences = []
        for sample, result in samples.values():
            output = original.step(Observation(schema_version="1", pixels=[p / 255 for p in sample.observation_u8]))
            assert result.output == output
            assert result.model_file_reads == 0
            assert sample.frame.evidence_kind == "fixture"
            sequences.append(sample.frame.sequence)
        assert sequences == sorted(set(sequences))
        assert session._child.poll() == 0 or session._child.poll() < 0
        assert session.capture.slot.closed
        assert not session.capture._thread.is_alive()
        ledger = LiveLedger.session(tmp_path, session.session_id, cap=3, mode="automated")
        assert ledger.attempted == 3
        assert not (tmp_path / "artifacts/live/validation/attempts.jsonl").exists()
        with LiveOwnership(tmp_path):
            pass
        session.start()
        assert session.snapshot().status.attempted_calls == 3
    finally:
        session.stop()


def test_second_session_and_p00_contend_before_capture(adapter_files, tmp_path):
    config = SessionConfig(source_id="fixture-pattern", evidence_kind="fixture", seed=1)
    first = NeuralSession(config, purpose="fixture", repository_root=tmp_path, files=adapter_files)
    second = NeuralSession(config, purpose="fixture", repository_root=tmp_path, files=adapter_files)
    try:
        first.start()
        with pytest.raises(BusyError):
            second.start()
        assert second.capture.slot.accepted == 0 and second._child is None
    finally:
        first.stop()
        second.stop()


def test_recording_and_unconfirmed_real_source_rejected(adapter_files, tmp_path):
    config = SessionConfig(source_id="fixture-pattern", evidence_kind="fixture", seed=1, recording=True)
    with pytest.raises(ValueError, match="recording"):
        NeuralSession(config, purpose="fixture", repository_root=tmp_path, files=adapter_files)
    config = SessionConfig(source_id="v4l2-video0", evidence_kind="real", seed=1)
    with pytest.raises(ValueError, match="operator-confirmed"):
        NeuralSession(config, purpose="fixture", repository_root=tmp_path, files=adapter_files)


def test_missing_model_fails_without_calls_or_fixture_fallback(tmp_path):
    config = SessionConfig(source_id="fixture-pattern", evidence_kind="fixture", seed=1)
    session = NeuralSession(config, purpose="fixture", repository_root=tmp_path,
                            files={"allow_fixture": True})
    session.start()
    try:
        snapshot, _ = collect(session)
        assert snapshot.status.state == "failed"
        assert snapshot.status.attempted_calls == 0
        assert snapshot.completed_calls == 0
    finally:
        session.stop()


def test_clock_admission_rejects_stale_input_and_sends_newest_only_once(adapter_files, tmp_path, monkeypatch):
    from flytrap.live import session as module

    config = SessionConfig(source_id="fixture-pattern", evidence_kind="fixture", seed=1)
    session = NeuralSession(config, purpose="fixture", repository_root=tmp_path, files=adapter_files)
    clock = SimpleNamespace(monotonic=lambda: 100.)
    monkeypatch.setattr(module, "time", clock)
    parent, child = socket.socketpair(socket.AF_UNIX, socket.SOCK_SEQPACKET)
    child.setblocking(False)
    session._channel = parent
    session._state, session._ready_time = "running", 100.
    session._started = session._lease = 100.
    try:
        session.capture.slot.put(fixture_frame(0, session.session_id, 1, receipt_monotonic_ms=97000.))
        session._schedule()
        assert session._pending is None
        with pytest.raises(BlockingIOError):
            receive_packet(child)
        for index in (1, 2, 3):
            session.capture.slot.put(fixture_frame(index, session.session_id, 1, receipt_monotonic_ms=100000.))
        session._schedule()
        request = receive_packet(child)
        assert request["step_index"] == 0
        assert session._pending.frame.sequence == 3
        session._schedule()
        with pytest.raises(BlockingIOError):
            receive_packet(child)
        # Taking the unread slot does not erase the last receipt's freshness.
        assert session.snapshot().source_receipt_age_ms == 0.
        assert session._latest_receipt == 100000.
    finally:
        parent.close()
        child.close()
