import os

from fastapi.testclient import TestClient
import pytest

from flytrap.api import create_app
from flytrap.config import Settings
from flytrap.contracts import Capabilities, ErrorResponse


def test_fixture_lifespan_owns_real_file_and_separate_worker(settings):
    app = create_app(settings)
    assert not settings.database_path.exists()
    assert not app.state.started
    with TestClient(app) as client:
        assert settings.database_path.is_file()
        assert settings.artifact_root.is_dir()
        assert app.state.worker.alive
        assert app.state.worker.pid != os.getpid()
        assert client.get("/health/live").json() == {"status": "ok"}
        assert client.get("/health/ready").status_code == 200
        config = Capabilities.model_validate(client.get("/api/config").json())
        assert config.fixture and not config.real_model_available
        assert config.admission == "closed"
        assert config.learning_claim_status == "NOT_RUN"
        assert client.post("/api/runs", json={}).status_code == 404
        app.state.worker.close()
        response = client.get("/health/ready")
        assert response.status_code == 503
        assert ErrorResponse.model_validate(response.json()).code == "unavailable"
    assert not app.state.worker.alive
    assert not app.state.started


def test_real_profile_reports_unavailability_without_fixture(settings):
    app = create_app(Settings(data_root=settings.data_root, artifact_root=settings.artifact_root))
    with TestClient(app) as client:
        assert client.get("/health/live").status_code == 200
        assert client.get("/health/ready").status_code == 503
        config = Capabilities.model_validate(client.get("/api/config").json())
        assert not config.fixture and not config.real_model_available
        assert config.admission == "unavailable"
        assert app.state.worker is None


def test_lifespan_rejects_unpatched_linked_sqlite(settings, monkeypatch):
    monkeypatch.setattr("sqlite3.sqlite_version_info", (3, 51, 2))
    app = create_app(settings)
    with pytest.raises(RuntimeError, match="SQLite"), TestClient(app):
        pass
    assert app.state.worker is None
    assert not settings.database_path.exists()
