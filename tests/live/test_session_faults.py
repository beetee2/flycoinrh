"""Actual processes and socket IPC; all sources and responses are synthetic."""
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

import pytest

from flytrap.live.accounting import BusyError, LiveLedger, LiveOwnership
from flytrap.live.session import NeuralSession
from tests.controllers import conftest as synthetic_fixtures
from tests.live.session_fault_worker import SyntheticCapture, config

adapter_files = synthetic_fixtures.adapter_files
adapter_files_factory = synthetic_fixtures.adapter_files_factory


def wait_until(condition, timeout=3):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(.01)
    raise AssertionError("bounded condition did not occur")


@pytest.fixture
def sessions(tmp_path, adapter_files):
    created = []

    def make(mode, **overrides):
        capture_factory = overrides.pop("capture_factory", SyntheticCapture)
        session = NeuralSession(config(**overrides), purpose="fixture", repository_root=tmp_path,
            files=adapter_files, capture_factory=capture_factory,
            worker_command=[sys.executable, "-m", "tests.live.session_fault_worker", mode])
        created.append(session)
        return session

    yield make
    for session in created:
        session.stop()
        assert session.wait(2)
        assert session._child is None or session._child.poll() is not None


def assert_released(session):
    assert session._child.poll() is not None
    assert not session.capture.thread.is_alive()
    assert session.capture.slot.closed
    with LiveOwnership(session.root):
        pass


@pytest.mark.parametrize("mode,reason,attempts", [
    ("startup_hang", "startup deadline", 0), ("startup_crash", None, 0),
    ("step_hang", "step deadline", 1), ("step_crash", None, 1),
])
def test_startup_and_step_faults_reap_child_and_release_source(sessions, mode, reason, attempts):
    session = sessions(mode, startup_deadline_ms=200 if mode == "startup_hang" else 1500,
                       step_deadline_ms=150)
    session.start()
    assert session.wait(2)
    snapshot = session.snapshot()
    assert snapshot.status.state == "failed"
    if reason:
        assert reason in snapshot.status.reason
    assert snapshot.status.attempted_calls == attempts
    assert snapshot.completed_calls == 0
    assert snapshot.sample is None
    assert_released(session)
    pid = session._child.pid
    assert session.start() is session
    assert session._child.pid == pid  # Terminal Start cannot resume work.


@pytest.mark.parametrize("mode", ["foreign", "future"])
def test_invalid_result_never_becomes_a_sample(sessions, mode):
    session = sessions(mode).start()
    assert session.wait(2)
    snapshot = session.snapshot()
    assert snapshot.status.state == "failed"
    assert snapshot.status.attempted_calls == 1
    assert snapshot.completed_calls == 0
    assert snapshot.sample is snapshot.last_inferred is None
    assert_released(session)


def test_stale_response_is_only_historical_and_stop_cannot_revive_it(sessions):
    session = sessions("stale", response_max_age_ms=80).start()
    wait_until(lambda: session.snapshot().completed_calls == 1)
    snapshot = session.snapshot()
    assert snapshot.status.state == "running"
    assert snapshot.sample is None
    assert snapshot.last_inferred is not None
    assert snapshot.rejected_results == 1
    session.stop()
    assert session.wait(1)
    assert session.snapshot().sample is None
    assert_released(session)


def test_control_lease_expires_while_waiting_for_worker(sessions):
    session = sessions("step_hang", lease_ms=600).start()
    wait_until(lambda: session.renew_lease() and session.snapshot().status.attempted_calls == 1)
    assert session.wait(2)
    assert session.snapshot().status.state == "stopped"
    assert "lease expired" in session.snapshot().status.reason
    assert not session.renew_lease()
    assert session.snapshot().sample is None
    assert_released(session)


def test_explicit_stop_kills_uncooperative_worker_promptly_and_new_session_can_start(sessions):
    session = sessions("step_hang").start()
    wait_until(lambda: session.snapshot().status.attempted_calls == 1)
    assert session.snapshot().waiting_for_sample
    started = time.monotonic()
    session.stop()
    assert time.monotonic() - started < 1.2
    assert session.wait(.1)
    assert session.snapshot().status.state == "stopped"
    assert session._child.returncode == -signal.SIGKILL
    assert_released(session)
    replacement = sessions("step_hang").start()
    wait_until(lambda: replacement.snapshot().status.attempted_calls == 1)
    assert replacement.session_id != session.session_id
    assert replacement._child.pid != session._child.pid


def test_source_loss_stops_pending_work(sessions):
    session = sessions("step_hang").start()
    wait_until(lambda: session.snapshot().status.attempted_calls == 1)
    session.capture.producer = "inactive"
    assert session.wait(1)
    assert session.snapshot().status.state == "source_lost"
    assert session.snapshot().sample is None
    assert_released(session)


def test_append_before_worker_crash_is_reconciled_without_notification(sessions):
    session = sessions("append_exit").start()
    assert session.wait(2)
    ledger = LiveLedger.session(session.root, session.session_id, mode="automated",
                                cap=session.config.max_model_calls)
    assert ledger.attempted == 1
    snapshot = session.snapshot()
    assert snapshot.status.state == "failed"
    assert snapshot.status.attempted_calls == 1
    assert snapshot.completed_calls == 0
    assert_released(session)


class BlockedStopCapture(SyntheticCapture):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.stop_entered = threading.Event()
        self.release_stop = threading.Event()

    def stop(self):
        self.stop_entered.set()
        self.release_stop.wait(4)
        super().stop()


class ReturningStopCapture(SyntheticCapture):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.stop_returned = threading.Event()

    def stop(self):
        # Match a capture backend reporting cleanup failure after its bounded
        # join expired. Returning is not evidence that its reader has finished.
        self.state = "failed"
        self.stop_returned.set()


def test_blocked_capture_cleanup_retains_ownership_until_capture_closes(sessions):
    session = sessions("step_hang", capture_factory=BlockedStopCapture, stop_grace_ms=300).start()
    wait_until(lambda: session.snapshot().status.attempted_calls == 1)
    try:
        started = time.monotonic()
        session.stop()
        assert time.monotonic() - started < .7
        assert session.capture.stop_entered.wait(.1)
        wait_until(lambda: session._child.poll() is not None, timeout=.5)
        with pytest.raises(BusyError):
            with LiveOwnership(session.root):
                pass
        assert session.snapshot().sample is None
    finally:
        session.capture.release_stop.set()
    assert session.wait(1)
    assert_released(session)


def test_returning_capture_stop_retains_lock_until_owned_thread_ends(sessions):
    session = sessions("step_hang", capture_factory=ReturningStopCapture, stop_grace_ms=300).start()
    wait_until(lambda: session.snapshot().status.attempted_calls == 1)
    try:
        started = time.monotonic()
        session.stop()
        assert time.monotonic() - started < .7
        assert session.capture.stop_returned.wait(.1)
        assert session.capture.thread.is_alive()
        wait_until(lambda: session._child.poll() is not None, timeout=.5)
        with pytest.raises(BusyError):
            with LiveOwnership(session.root):
                pass
        assert session.snapshot().sample is None
    finally:
        SyntheticCapture.stop(session.capture)
    assert session.wait(1)
    assert_released(session)


def test_ownership_inode_replacement_stops_live_worker(sessions):
    session = sessions("step_hang").start()
    wait_until(lambda: session.snapshot().status.attempted_calls == 1)
    lock = session.root / "artifacts/live/session.lock"
    replacement = lock.with_suffix(".replacement")
    replacement.write_bytes(b"")
    os.replace(replacement, lock)
    assert session.wait(1)
    assert session.snapshot().status.state == "failed"
    assert session.snapshot().sample is None
    assert_released(session)


def alive(pid):
    try:
        return Path(f"/proc/{pid}/stat").read_text().split()[2] != "Z"
    except FileNotFoundError:
        return False


def test_parent_death_kills_child_and_releases_p00_lock(tmp_path, adapter_files):
    files_path = tmp_path / "synthetic-files.json"
    files_path.write_text(json.dumps({k: str(v) if isinstance(v, Path) else v for k, v in adapter_files.items()}))
    ready = tmp_path / "child-ready.json"
    parent = subprocess.Popen([sys.executable, "-m", "tests.live.session_fault_worker", "parent_probe",
                               str(tmp_path), str(files_path), str(ready)],
                              stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    worker_pid = None
    try:
        wait_until(lambda: ready.exists() or parent.poll() is not None)
        assert parent.poll() is None, parent.stderr.read().decode()
        worker_pid = json.loads(ready.read_text())["worker_pid"]
        assert alive(worker_pid)
        # P00 is excluded during the active session. The guarded child must die
        # with its supervisor and all inherited descriptors must then close.
        with (tmp_path / "artifacts/milestones/P00/model.lock").open("rb") as stream:
            with pytest.raises(BlockingIOError):
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            parent.kill()
            parent.wait(timeout=1)
            wait_until(lambda: not alive(worker_pid), timeout=1)
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with LiveOwnership(tmp_path):
            pass
    finally:
        if parent.poll() is None:
            parent.kill()
        parent.wait(timeout=2)
        parent.stderr.close()
        if worker_pid is not None and alive(worker_pid):
            os.kill(worker_pid, signal.SIGKILL)
