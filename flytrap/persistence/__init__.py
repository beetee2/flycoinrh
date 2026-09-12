"""File-backed SQLite connection policy; domain migrations arrive in milestone 06."""
from contextlib import contextmanager
from pathlib import Path
import sqlite3

MIN_SQLITE = (3, 51, 3)


def require_sqlite(version: tuple[int, ...] | None = None) -> None:
    actual = sqlite3.sqlite_version_info if version is None else version
    if actual < MIN_SQLITE:
        raise RuntimeError(f"SQLite {actual} rejected: linked library must be at least {MIN_SQLITE}")


@contextmanager
def connect_database(path: Path):
    require_sqlite()
    path = Path(path)
    if str(path) == ":memory:":
        raise ValueError("FLYTRAP requires a file-backed database")
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=1.0)
    try:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=1000")
        mode = connection.execute("PRAGMA journal_mode=WAL").fetchone()[0]
        if mode != "wal":
            raise RuntimeError("SQLite WAL was not enabled")
        yield connection
    finally:
        connection.close()
