"""Filesystem/process accounting boundaries; all calls are synthetic fixtures."""
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from flytrap.live.accounting import (
    AUTOMATED_CAP, BudgetExceeded, BusyError, LedgerCorrupt, LiveLedger, LiveOwnership,
)


def append(ledger, ownership, *, step=0, session_id="fixture-session"):
    return ledger.record_attempt(session_id=session_id, seed=17, step=step, ownership=ownership)


def test_fixed_automated_path_and_p00_preserved_across_restarts(tmp_path):
    p00 = tmp_path / "artifacts/milestones/P00/attempts.jsonl"
    p00.parent.mkdir(parents=True)
    original = b'{"historical":"fixture"}\n'
    p00.write_bytes(original)
    ledger = LiveLedger.automated(tmp_path)
    assert ledger.path == tmp_path / "artifacts/live/validation/attempts.jsonl"
    assert ledger.remaining == AUTOMATED_CAP
    with LiveOwnership(tmp_path) as owner:
        assert append(ledger, owner) == 1
        # A failed invocation remains charged; no success/result event is needed.
        with pytest.raises(RuntimeError, match="synthetic model failure"):
            raise RuntimeError("synthetic model failure")
    restarted = LiveLedger.automated(tmp_path)
    assert restarted.attempted == 1
    assert restarted.remaining == 1023
    assert p00.read_bytes() == original


def test_fsync_completes_before_call_and_failure_never_reaches_call(tmp_path, monkeypatch):
    ledger = LiveLedger.automated(tmp_path)
    assert ledger.attempted == 0
    real_fsync = os.fsync
    synced = []

    def track(fd):
        real_fsync(fd)
        synced.append(Path(f"/proc/self/fd/{fd}").resolve().name)

    with LiveOwnership(tmp_path) as owner:
        monkeypatch.setattr(os, "fsync", track)
        append(ledger, owner)
        # This is the exact gate immediately before a synthetic model call.
        assert "attempts.jsonl" in synced
        assert "attempts.state.tmp" in synced
        assert synced.index("attempts.jsonl") < synced.index("attempts.state.tmp")
        assert LiveLedger.automated(tmp_path).attempted == 1

        def fail(fd):
            raise OSError("fixture fsync failure")

        monkeypatch.setattr(os, "fsync", fail)
        called = False
        with pytest.raises(OSError, match="fixture fsync failure"):
            append(ledger, owner, step=1)
            called = True
        assert not called
        # Appended row with an old checkpoint fails closed after restart.
        with pytest.raises(LedgerCorrupt):
            LiveLedger.automated(tmp_path).attempted


@pytest.mark.parametrize("damage", ["partial", "json", "delete", "truncate", "edit", "state", "state-delete"])
def test_corruption_never_grants_new_allowance(tmp_path, damage):
    ledger = LiveLedger.automated(tmp_path)
    with LiveOwnership(tmp_path) as owner:
        append(ledger, owner)
        if damage == "partial":
            with ledger.path.open("ab") as stream:
                stream.write(b'{"attempt":')
        elif damage == "json":
            ledger.path.write_text("not json\n")
        elif damage == "delete":
            ledger.path.unlink()
        elif damage == "truncate":
            ledger.path.write_bytes(b"")
        elif damage == "edit":
            row = json.loads(ledger.path.read_text())
            row["seed"] = 99
            ledger.path.write_text(json.dumps(row) + "\n")
        elif damage == "state":
            ledger.checkpoint.write_text("{}")
        else:
            ledger.checkpoint.unlink()
        restarted = LiveLedger.automated(tmp_path)
        with pytest.raises(LedgerCorrupt):
            restarted.remaining
        with pytest.raises(LedgerCorrupt):
            append(restarted, owner, step=1)


def test_real_ceiling_and_session_budget_are_independent(tmp_path):
    ledger = LiveLedger.automated(tmp_path)
    with LiveOwnership(tmp_path) as owner:
        # Actual durable appends exercise the published 1024 limit, not a mock cap.
        for index in range(AUTOMATED_CAP):
            append(ledger, owner, session_id=f"fixture-{index // 512}", step=index % 512)
        assert ledger.remaining == 0
        with pytest.raises(BudgetExceeded):
            append(ledger, owner)
        human = LiveLedger.session(tmp_path, "fixture-human", cap=2, mode="human")
        for step in range(2):
            append(human, owner, step=step, session_id="fixture-human")
        with pytest.raises(BudgetExceeded):
            append(human, owner, step=2, session_id="fixture-human")
        assert LiveLedger.session(tmp_path, "fixture-human", cap=2).attempted == 2
        assert ledger.attempted == 1024
        with pytest.raises(LedgerCorrupt):
            LiveLedger.session(tmp_path, "fixture-human", cap=512).attempted


@pytest.mark.parametrize("kwargs", [
    {"cap": 513}, {"cap": 0}, {"cap": True}, {"session_id": "../escape"}, {"mode": "manual-retry"},
])
def test_invalid_accounting_configuration(tmp_path, kwargs):
    with pytest.raises(ValueError):
        LiveLedger(tmp_path, **kwargs)


def test_foreign_session_seed_step_and_missing_ownership_rejected(tmp_path):
    ledger = LiveLedger.session(tmp_path, "fixture-session", mode="automated")
    owner = LiveOwnership(tmp_path)
    with pytest.raises(RuntimeError, match="ownership"):
        append(ledger, owner)
    with owner:
        for call in (dict(session_id="foreign", seed=1, step=0),
                     dict(session_id="fixture-session", seed=True, step=0),
                     dict(session_id="fixture-session", seed=1, step=512)):
            with pytest.raises(ValueError):
                ledger.record_attempt(**call, ownership=owner)
        assert ledger.attempted == 0


def test_shared_p00_contention_and_failed_acquisition_releases_live_lock(tmp_path):
    path = tmp_path / "artifacts/milestones/P00/model.lock"
    path.parent.mkdir(parents=True)
    with path.open("a") as p00:
        fcntl.flock(p00, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(BusyError):
            LiveOwnership(tmp_path).acquire()
    with LiveOwnership(tmp_path):
        with path.open("a") as p00:
            with pytest.raises(BlockingIOError):
                fcntl.flock(p00, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(BusyError):
            LiveOwnership(tmp_path).acquire()
    with LiveOwnership(tmp_path):
        pass


def test_child_inherits_ownership_and_parent_close_cannot_unlock(tmp_path):
    owner = LiveOwnership(tmp_path).acquire()
    child = subprocess.Popen([
        sys.executable, "-c",
        "import sys; from pathlib import Path; "
        "from flytrap.live.accounting import LiveOwnership, LiveLedger; "
        "owner=LiveOwnership.from_inherited(Path(sys.argv[1]),tuple(map(int,sys.argv[2:]))); "
        "ledger=LiveLedger.automated(Path(sys.argv[1])); "
        "ledger.record_attempt(session_id='fixture-child',seed=1,step=0,ownership=owner); "
        "print('ready',flush=True); sys.stdin.readline(); owner.close()",
        str(tmp_path), *map(str, owner.filenos),
    ], pass_fds=owner.filenos, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        assert child.stdout.readline().strip() == "ready"
        owner.close()
        with pytest.raises(BusyError):
            LiveOwnership(tmp_path).acquire()
        assert LiveLedger.automated(tmp_path).attempted == 1
        child.communicate("stop\n", timeout=3)
        assert child.returncode == 0
        with LiveOwnership(tmp_path):
            pass
    finally:
        owner.close()
        if child.poll() is None:
            child.kill()
            child.wait(timeout=3)


def test_replaced_lock_identity_fails_closed(tmp_path):
    with LiveOwnership(tmp_path) as owner:
        owner.paths[0].unlink()
        owner.paths[0].touch()
        with pytest.raises(RuntimeError, match="identity"):
            append(LiveLedger.automated(tmp_path), owner)


def test_accounting_lock_contention_is_nonblocking(tmp_path):
    ledger = LiveLedger.automated(tmp_path)
    assert ledger.attempted == 0
    with ledger.lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(BusyError):
            ledger.attempted
