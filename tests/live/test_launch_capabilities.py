"""Launch-profile and error boundaries using metadata and fixtures only."""
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from flytrap.live.api import create_live_app
from flytrap.live.api_contracts import ApiError, ERROR_MESSAGES, StartRequest
from flytrap.live.contracts import SessionConfig
from flytrap.live.service import LiveService, Unavailable, safe_source_metadata


def test_normal_live_metadata_reads_remain_idle(tmp_path, monkeypatch):
    from flytrap.live import environment
    calls = []

    def metadata():
        calls.append("metadata-only")
        return {"devices": []}

    def forbidden(*args, **kwargs):
        raise AssertionError("idle metadata reads cannot capture or infer")

    monkeypatch.setattr(environment, "discover_devices", metadata)
    service = LiveService(repository_root=tmp_path, execution_purpose="human",
        session_factory=forbidden, capture_factory=forbidden)
    with TestClient(create_live_app(service=service), base_url="http://127.0.0.1") as client:
        for _ in range(2):
            assert client.get("/api/live/capabilities").json() == {
                "schema_version": "obs-capabilities-1", "profile": "live",
                "preview": True, "inference": True, "replay": True, "neural_backend": "cpu"}
            assert client.get("/api/live/sources").json()["sources"] == []
            assert client.get("/api/live/status").json()["current"] is None
        assert calls == ["metadata-only", "metadata-only"]
        assert service.sessions == {}
    assert not (tmp_path / "artifacts").exists()


def test_safe_source_retains_normal_neural_factory_and_human_execution(tmp_path, monkeypatch):
    from flytrap.live import session
    calls = []

    def neural_constructor(config, **kwargs):
        calls.append((config, kwargs))
        raise Unavailable("Fixture stops at neural-session constructor; no model or capture calls.")

    monkeypatch.setattr(session, "NeuralSession", neural_constructor)
    service = LiveService(repository_root=tmp_path, source_provider=safe_source_metadata,
        execution_purpose="human")
    assert service.capabilities.inference is True
    with pytest.raises(ValidationError):
        service.capabilities.inference = False
    with pytest.raises(AttributeError):
        service.capabilities = None
    request = StartRequest(request_id="a"*32, owner_token="b"*32,
        config=SessionConfig(source_id="fixture-pattern", evidence_kind="fixture", seed=17))
    with pytest.raises(Unavailable, match="Fixture stops"):
        service.start(request)
    assert len(calls) == 1
    config, kwargs = calls[0]
    assert config == request.config
    assert kwargs["purpose"] == "human"
    assert kwargs["source"].backend == "synthetic"
    assert kwargs["expected_device"] is None
    assert not service.sessions
    assert not (tmp_path / "artifacts").exists()


@pytest.mark.parametrize("exception, status, code", [
    (Unavailable, 503, "source_unavailable"),
    (OSError, 503, "service_unavailable"),
    (RuntimeError, 500, "internal_error"),
])
def test_api_never_exposes_exception_text(tmp_path, exception, status, code):
    secret = "<script>alert('secret-token')</script> Traceback /home/private/key.pem"

    def source_failure():
        raise exception(secret)

    service = LiveService(repository_root=tmp_path, source_provider=source_failure)
    with TestClient(create_live_app(service=service), base_url="http://127.0.0.1",
                    raise_server_exceptions=False) as client:
        response = client.get("/api/live/sources")
        assert response.status_code == status
        error = ApiError.model_validate(response.json())
        assert error.code == code and error.message == ERROR_MESSAGES[code]
        assert "secret" not in response.text and "Traceback" not in response.text
        assert len(response.content) < 512
        assert response.headers["cache-control"] == "no-store"


def test_security_and_validation_errors_are_actionable_without_echoing_input(tmp_path):
    service = LiveService(repository_root=tmp_path, source_provider=lambda: [])
    with TestClient(create_live_app(service=service), base_url="http://127.0.0.1") as client:
        response = client.post("/api/live/sessions", json={})
        assert response.json()["code"] == "origin_required"
        response = client.post("/api/live/sessions", json={}, headers={"Origin": "http://127.0.0.1"})
        assert response.json()["code"] == "csrf_required"
        token = client.get("/api/live/control").json()["csrf_token"]
        response = client.post("/api/live/sessions", json={"secret": "<script>private input</script>"},
            headers={"Origin": "http://127.0.0.1", "X-Live-CSRF": token})
        assert response.status_code == 422
        assert response.json()["code"] == "invalid_request"
        assert "private input" not in response.text
        ApiError.model_validate(response.json())
        assert not service.sessions
