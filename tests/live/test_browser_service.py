"""OBS05 server policy tests; no source devices or full model calls."""
import uuid

from fastapi.testclient import TestClient
import pytest

from flytrap.live.api import create_live_app
from flytrap.live.api_contracts import StartRequest
from flytrap.live.contracts import SessionConfig
from flytrap.live.service import LiveService, neural_factory, safe_source_metadata


def test_default_real_factory_accounts_api_work_as_automated(monkeypatch, tmp_path):
    from flytrap.live import session
    calls = []
    monkeypatch.setattr(session, "NeuralSession", lambda config, **kwargs: calls.append(kwargs))
    config = SessionConfig(source_id="fixture-pattern", evidence_kind="fixture", seed=17)
    for policy in (None, "human"):
        kwargs = {} if policy is None else {"execution_purpose": policy}
        neural_factory(config, repository_root=tmp_path, source=safe_source_metadata()[0],
                       expected_device=None, recording_store=None, **kwargs)
    assert [call["purpose"] for call in calls] == ["automated", "human"]
    assert all(call["source"].source_id == "fixture-pattern" for call in calls)


@pytest.mark.parametrize("location", ["request", "config"])
def test_browser_cannot_select_execution_purpose(location, tmp_path):
    service = LiveService(repository_root=tmp_path, source_provider=safe_source_metadata)
    with TestClient(create_live_app(service=service), base_url="http://127.0.0.1") as client:
        token = client.get("/api/live/control").json()["csrf_token"]
        body = StartRequest(request_id=uuid.uuid4().hex, owner_token=uuid.uuid4().hex,
            config=SessionConfig(source_id="fixture-pattern", evidence_kind="fixture", seed=17)).model_dump()
        (body if location == "request" else body["config"])["execution_purpose"] = "human"
        response = client.post("/api/live/sessions", json=body,
            headers={"Origin": "http://127.0.0.1", "X-Live-CSRF": token})
        assert response.status_code == 422
        assert service.sessions == {}
        assert not (tmp_path / "artifacts").exists()


def test_cli_safe_source_configuration_remains_idle_and_server_controlled(monkeypatch):
    import uvicorn
    from flytrap.live.__main__ import main
    calls = []
    monkeypatch.setattr(uvicorn, "run", lambda app, **kwargs: calls.append((app, kwargs)))
    assert main(["serve", "--port", "8877", "--safe-source"]) == 0
    app, options = calls[0]
    service = app.state.service
    assert options["host"] == "127.0.0.1" and options["port"] == 8877
    assert service.execution_purpose == "automated"
    assert service.sources().sources == safe_source_metadata()
    assert service.current_id is None and not service.sessions
    assert main(["serve", "--execution-purpose", "human"]) == 0
    assert calls[1][0].state.service.execution_purpose == "human"


def test_monitor_recording_is_rejected_before_creating_session(tmp_path, monkeypatch):
    from flytrap.live.contracts import SourceCapability
    from flytrap.live.service import Forbidden
    source = SourceCapability(schema_version="obs-source-1", source_id="v4l2-video0",
        evidence_kind="real", name="Declared OBS metadata fixture", driver="v4l2 loopback",
        backend="ffmpeg-v4l2", capabilities=None, formats=None, metadata_state="available",
        producer_detection="driver")
    service = LiveService(repository_root=tmp_path)
    monkeypatch.setattr(service, "_source", lambda _: (source, None))
    request = StartRequest(request_id=uuid.uuid4().hex, owner_token=uuid.uuid4().hex,
        recording_consent=True, config=SessionConfig(source_id=source.source_id,
            evidence_kind="real", seed=17, recording=True))
    with pytest.raises(Forbidden, match="Recording the selected OBS source is disabled"):
        service.start(request)
    assert not service.sessions and service.recording_store is None
    assert not (tmp_path / "artifacts").exists()


def test_config_reads_existing_accounting_and_fails_closed_on_corruption(tmp_path):
    from flytrap.live.accounting import LiveLedger, LiveOwnership
    service = LiveService(repository_root=tmp_path)
    assert service.config().validation_remaining == 1024
    assert not (tmp_path / "artifacts").exists()
    ledger = LiveLedger.automated(tmp_path)
    with LiveOwnership(tmp_path) as owner:
        ledger.record_attempt(session_id="fixture-budget", seed=17, step=0, ownership=owner)
    config = service.config()
    assert config.validation_attempted == 1 and config.validation_remaining == 1023
    ledger.checkpoint.write_text("invalid accounting fixture")
    assert service.config().validation_remaining is None
    assert service.config().validation_attempted is None
