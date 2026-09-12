import sqlite3

import pytest

from flytrap.persistence import connect_database


def test_real_file_connections_visibility_rollback_and_policy(tmp_path):
    path = tmp_path / "database.sqlite3"
    with connect_database(path) as writer, connect_database(path) as reader:
        assert path.is_file()
        assert writer.execute("PRAGMA database_list").fetchone()[2] == str(path)
        assert writer.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert writer.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert writer.execute("PRAGMA busy_timeout").fetchone()[0] == 1000
        writer.execute("CREATE TABLE probe (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
        with writer:
            writer.execute("INSERT INTO probe VALUES (1, 'committed')")
        assert reader.execute("SELECT value FROM probe").fetchall() == [("committed",)]
        with pytest.raises(sqlite3.IntegrityError), writer:
            writer.execute("INSERT INTO probe VALUES (2, 'rolled back')")
            writer.execute("INSERT INTO probe VALUES (1, 'duplicate')")
        assert reader.execute("SELECT COUNT(*) FROM probe").fetchone()[0] == 1
    with pytest.raises(sqlite3.ProgrammingError):
        writer.execute("SELECT 1")
    with connect_database(path) as restored:
        assert restored.execute("SELECT value FROM probe").fetchone() == ("committed",)
