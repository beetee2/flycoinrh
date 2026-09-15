"""Disk-fault lifecycle tests using tiny synthetic models and generated RGB only.

The normal neural subprocess, real private temporary files and real source thread
remain in the path. These tests never access a device or the full-model ledgers.
"""
import threading
import time

import pytest

from flytrap.live.accounting import LiveOwnership
from flytrap.live.contracts import SessionConfig, SourceCapability
from flytrap.live.recording import Recorder, RecordingError, RecordingStore
from flytrap.live.session import NeuralSession
from tests.controllers import conftest as synthetic_fixtures
from tests.live.session_fault_worker import SyntheticCapture

adapter_files = synthetic_fixtures.adapter_files
adapter_files_factory = synthetic_fixtures.adapter_files_factory


def eventually(predicate, timeout=3):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(.01)
    raise AssertionError("bounded disk-fault lifecycle condition did not occur")


@pytest.fixture
def recording_session(tmp_path, adapter_files):
    sessions = []
    store = RecordingStore(tmp_path / "recordings")
    source = SourceCapability(schema_version="obs-source-1", source_id="fixture-pattern",
        evidence_kind="fixture", name="Synthetic recording fault fixture", driver=None,
        backend="synthetic", capabilities=None, formats=None, metadata_state="available",
        producer_detection="synthetic")

    def create(**overrides):
        config = SessionConfig(source_id="fixture-pattern", evidence_kind="fixture", seed=17,
            recording=True, **{"max_model_calls": 2, "duration_seconds": 8,
                "startup_deadline_ms": 5000, "stop_grace_ms": 1000, **overrides})
        session = NeuralSession(config, purpose="fixture", repository_root=tmp_path,
            files=adapter_files, capture_factory=SyntheticCapture, recording_store=store, source=source)
        sessions.append(session)
        return session

    yield create, store
    for session in sessions:
        session.stop()
        assert session.wait(2)
        session._thread.join(2)
        assert not session._thread.is_alive()
        assert session._child is None or session._child.poll() is not None
        assert session.capture.slot.closed
        assert not session.capture.thread.is_alive()
    with LiveOwnership(tmp_path):
        pass
    assert not (tmp_path / "artifacts/live/validation/attempts.jsonl").exists()


def await_write(session, entered):
    deadline = time.monotonic() + 5
    while not entered.wait(.01):
        assert time.monotonic() < deadline, "synthetic session never reached recording write"
        assert session.renew_lease(), session.snapshot()


@pytest.mark.parametrize("method", ["append_input", "append_sample"])
@pytest.mark.parametrize("ending", ["stop", "lease"])
def test_stalled_recording_cannot_hold_neural_or_source_resources(recording_session, monkeypatch,
                                                               method, ending):
    create, store = recording_session
    entered, release = threading.Event(), threading.Event()
    original = getattr(Recorder, method)

    def stalled(writer, *args):
        entered.set()
        assert release.wait(8), "test did not release synthetic disk stall"
        return original(writer, *args)

    monkeypatch.setattr(Recorder, method, stalled)
    session = create(lease_ms=700).start()
    stopped = threading.Event()
    stopper = None
    try:
        await_write(session, entered)
        child = session._child
        assert child is not None and child.poll() is None
        if ending == "stop":
            def stop():
                session.stop()
                stopped.set()
            stopper = threading.Thread(target=stop, daemon=True)
            began = time.monotonic()
            stopper.start()
            assert stopped.wait(3.2), "Stop blocked behind a recording write"
            assert time.monotonic() - began < 3.2
        eventually(lambda: child.poll() is not None and session.capture.slot.closed, timeout=2.3)
        # Resource exit precedes the coordinator's final accounting/lock release.
        # Wait for its explicit cleanup completion signal before claiming the slot.
        assert session.wait(.5)
        assert not session.capture.thread.is_alive()
        snapshot = session.snapshot()
        assert snapshot.flight.neutral and snapshot.flight.speed_units_s == 0
        assert session.recording_state != "complete"
        if ending == "lease":
            assert "lease" in snapshot.status.reason.lower()
        with LiveOwnership(session.root):
            pass
        with pytest.raises(RecordingError):
            store.read(session.recording_id)
    finally:
        release.set()
        if stopper:
            stopper.join(2)
        session.stop()
        session._thread.join(2)
    assert session.recording_state == "aborted"
    assert not (store.root / session.recording_id / "complete.sha256").exists()
    with pytest.raises(RecordingError):
        store.read(session.recording_id)


@pytest.mark.parametrize("method", ["append_input", "append_sample"])
def test_disk_write_error_fails_session_and_keeps_artifact_incomplete(recording_session, monkeypatch, method):
    create, store = recording_session

    def failed(*args):
        raise OSError("synthetic ENOSPC write failure")

    monkeypatch.setattr(Recorder, method, failed)
    session = create().start()
    deadline = time.monotonic() + 5
    while not session.wait(.01):
        assert time.monotonic() < deadline
        session.renew_lease()
    session._thread.join(2)
    assert not session._thread.is_alive()
    snapshot = session.snapshot()
    assert snapshot.status.state == "failed"
    assert snapshot.flight.neutral
    assert session._child.poll() is not None
    assert session.capture.slot.closed
    assert session.recording_state == "aborted"
    assert snapshot.status.attempted_calls == (0 if method == "append_input" else 1)
    with pytest.raises(RecordingError):
        store.read(session.recording_id)
    assert not (store.root / session.recording_id / "complete.sha256").exists()


def test_response_that_ages_during_recording_never_applies_flight_control(recording_session, monkeypatch):
    create, store = recording_session
    original = Recorder.append_sample

    def slow(writer, *args):
        time.sleep(.15)
        return original(writer, *args)

    monkeypatch.setattr(Recorder, "append_sample", slow)
    session = create(response_max_age_ms=100).start()
    deadline = time.monotonic() + 5
    while not session.wait(.01):
        assert time.monotonic() < deadline
        session.renew_lease()
    session._thread.join(2)
    assert not session._thread.is_alive()
    snapshot = session.snapshot()
    assert snapshot.status.state == "limit_reached", snapshot
    assert snapshot.completed_calls == snapshot.rejected_results == 2
    assert session.flight_events == []
    assert snapshot.flight.neutral and snapshot.flight.applied_response_id is None
    restored = store.read(session.recording_id)
    assert len(restored.samples) == 2
    assert restored.trace.events == []
    assert all(state.snapshot.neutral for state in restored.states)
