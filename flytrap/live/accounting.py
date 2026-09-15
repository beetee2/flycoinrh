"""Durable live attempt accounting and inherited lifetime model ownership.

Lock order is live session, P00 model, ledger. Close inherited descriptors without
LOCK_UN: the worker keeps ownership when its supervising parent exits. Workers
must independently stop on parent loss; these locks prevent overlapping models
while that shutdown happens. No input pixels or source labels enter the ledger.
"""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time

AUTOMATED_CAP = 1024
SESSION_CAP = 512
_EMPTY_DIGEST = "0" * 64
_ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}\Z")


class BusyError(RuntimeError):
    """Another live/P00 owner already holds the resource."""


class BudgetExceeded(RuntimeError):
    """The durable attempted-call ceiling has been reached."""


class LedgerCorrupt(ValueError):
    """Accounting cannot establish a safe remaining allowance."""


def _open(path: Path) -> int:
    fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise ValueError("accounting paths must be regular files")
    return fd


class LiveOwnership:
    """Nonblocking process exclusion; use pass_fds=owner.filenos for Popen."""

    def __init__(self, repository_root: Path):
        self.root = Path(repository_root).resolve()
        self.paths = (self.root / "artifacts/live/session.lock",
                      self.root / "artifacts/milestones/P00/model.lock")
        self._fds: list[int] = []

    def acquire(self):
        if self._fds:
            return self
        try:
            for path in self.paths:
                path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                fd = _open(path)
                self._fds.append(fd)
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    raise BusyError("a live session or P00 model job already owns the model") from None
        except BaseException:
            self.close()
            raise
        return self

    @classmethod
    def from_inherited(cls, repository_root: Path, filenos):
        """Attach trusted child arguments, retaining the inherited open descriptions.

        No new flock is acquired: acquisition on a second open description would
        conflict with our own owner. This is internal worker plumbing, never an API.
        """
        owner = cls(repository_root)
        if len(filenos) != 2 or len(set(filenos)) != 2:
            raise ValueError("two distinct inherited ownership descriptors required")
        owner._fds = list(filenos)
        owner.require_active(repository_root)
        return owner

    @property
    def filenos(self):
        self.require_active(self.root)
        return tuple(self._fds)

    def require_active(self, repository_root: Path):
        if self.root != Path(repository_root).resolve() or len(self._fds) != 2:
            raise RuntimeError("live model ownership is required before recording an attempt")
        for path, fd in zip(self.paths, self._fds, strict=True):
            opened, current = os.fstat(fd), path.stat(follow_symlinks=False)
            if (opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino):
                raise RuntimeError("model ownership lock identity changed")
            if not stat.S_ISREG(current.st_mode):
                raise RuntimeError("model ownership lock is not a regular file")

    def close(self):
        # LOCK_UN would release the shared open description in surviving children.
        for fd in reversed(self._fds):
            os.close(fd)
        self._fds.clear()

    def __enter__(self):
        return self.acquire()

    def __exit__(self, *_):
        self.close()


def _json(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _sync_directory(path: Path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class LiveLedger:
    """Strict hash chain plus durable checkpoint, with a fixed workstream path.

    Missing, shortened or modified rows fail closed if the independent checkpoint
    survives. A crash between row and checkpoint publication also fails closed;
    recovery never guesses a fresh allowance. Removing all accounting artifacts
    is outside this local accidental-corruption protection.
    """

    def __init__(self, repository_root: Path, *, session_id=None, cap=SESSION_CAP, mode="automated"):
        self.root = Path(repository_root).resolve()
        if mode not in {"automated", "human"}:
            raise ValueError("unknown accounting mode")
        if type(cap) is not int or not 1 <= cap <= SESSION_CAP:
            raise ValueError("session cap must be between 1 and 512")
        if session_id is not None and (not isinstance(session_id, str) or not _ID.fullmatch(session_id)):
            raise ValueError("invalid server session ID")
        if session_id is None and mode != "automated":
            raise ValueError("human accounting requires an explicit session")
        self.session_id = session_id
        self.cap = AUTOMATED_CAP if session_id is None else cap
        self.scope = "automated" if session_id is None else f"{mode}-session:{session_id}"
        directory = (self.root / "artifacts/live/validation" if session_id is None else
                     self.root / "artifacts/live/sessions" / session_id)
        self.path = directory / "attempts.jsonl"
        self.checkpoint = directory / "attempts.state.json"
        self.lock_path = directory / "attempts.lock"

    @classmethod
    def automated(cls, repository_root: Path):
        return cls(repository_root)

    @classmethod
    def session(cls, repository_root: Path, session_id: str, *, cap=SESSION_CAP, mode="human"):
        return cls(repository_root, session_id=session_id, cap=cap, mode=mode)

    @contextmanager
    def _locked(self):
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        fd = _open(self.lock_path)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        except BlockingIOError:
            raise BusyError("live accounting is busy") from None
        finally:
            os.close(fd)

    def _save_state(self, count, digest):
        # Fixed temp is safe under accounting flock. It is never a replacement
        # ledger or lock inode. Leftover temp after interruption grants no calls.
        temp = self.checkpoint.with_suffix(".tmp")
        fd = _open(temp)
        try:
            os.ftruncate(fd, 0)
            self._write_all(fd, _json(dict(version=1, scope=self.scope, cap=self.cap,
                                          count=count, digest=digest)) + b"\n")
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(temp, self.checkpoint)
        _sync_directory(self.path.parent)

    @staticmethod
    def _write_all(fd, data):
        while data:
            written = os.write(fd, data)
            if written <= 0:
                raise OSError("attempt ledger write made no progress")
            data = data[written:]

    def _read(self):
        try:
            return self._read_checked()
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise LedgerCorrupt("live attempt ledger is missing or corrupt; fail closed") from exc

    def _read_checked(self):
        exists = self.path.exists(), self.checkpoint.exists()
        if exists == (False, False):
            # First persist the marker. If creation is interrupted, fail closed.
            self._save_state(0, _EMPTY_DIGEST)
            fd = _open(self.path)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
            _sync_directory(self.path.parent)
        elif exists != (True, True):
            raise LedgerCorrupt("missing ledger or accounting checkpoint")
        for path in (self.path, self.checkpoint):
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
                raise LedgerCorrupt("invalid ledger file")
        state = json.loads(self.checkpoint.read_bytes())
        raw = self.path.read_bytes()
        if raw and not raw.endswith(b"\n"):
            raise LedgerCorrupt("partial attempt row")
        rows = raw.splitlines()
        if len(rows) > self.cap:
            raise LedgerCorrupt("ledger exceeds authorized cap")
        digest = _EMPTY_DIGEST
        for number, line in enumerate(rows, 1):
            row = json.loads(line)
            if not isinstance(row, dict) or set(row) != {
                    "version", "scope", "attempt", "session_id", "seed", "step", "started_ns", "previous"}:
                raise LedgerCorrupt("invalid attempt fields")
            self._validate_call(row["session_id"], row["seed"], row["step"])
            if (type(row["version"]) is not int or row["version"] != 1 or row["scope"] != self.scope or
                    type(row["attempt"]) is not int or row["attempt"] != number or
                    type(row["started_ns"]) is not int or row["started_ns"] < 0 or row["previous"] != digest):
                raise LedgerCorrupt("invalid attempt sequence or identity")
            digest = hashlib.sha256(line).hexdigest()
        expected = dict(version=1, scope=self.scope, cap=self.cap, count=len(rows), digest=digest)
        if (state != expected or type(state.get("version")) is not int or
                type(state.get("cap")) is not int or type(state.get("count")) is not int):
            raise LedgerCorrupt("ledger does not match durable checkpoint")
        return len(rows), digest

    def _validate_call(self, session_id, seed, step):
        if not isinstance(session_id, str) or not _ID.fullmatch(session_id):
            raise ValueError("invalid server session ID")
        if self.session_id is not None and session_id != self.session_id:
            raise ValueError("foreign session accounting")
        if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
            raise ValueError("invalid session seed")
        if type(step) is not int or not 0 <= step < SESSION_CAP:
            raise ValueError("invalid model step")

    @property
    def attempted(self):
        with self._locked():
            return self._read()[0]

    @property
    def remaining(self):
        return self.cap - self.attempted

    def record_attempt(self, *, session_id: str, seed: int, step: int, ownership: LiveOwnership):
        """Return only after durable accounting; invoke the model AFTER this returns."""
        ownership.require_active(self.root)
        self._validate_call(session_id, seed, step)
        with self._locked():
            count, digest = self._read()
            if count >= self.cap:
                raise BudgetExceeded(f"{self.scope} attempted-call cap reached")
            row = dict(version=1, scope=self.scope, attempt=count + 1, session_id=session_id,
                       seed=seed, step=step, started_ns=time.time_ns(), previous=digest)
            line = _json(row)
            fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CLOEXEC | os.O_NOFOLLOW)
            try:
                self._write_all(fd, line + b"\n")
                os.fsync(fd)
            finally:
                os.close(fd)
            self._save_state(count + 1, hashlib.sha256(line).hexdigest())
            return count + 1
