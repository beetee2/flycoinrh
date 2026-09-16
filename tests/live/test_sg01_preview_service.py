"""Safe SG01 development service cannot open desktop sources or invoke a model."""
import subprocess
import time

from fastapi.testclient import TestClient
import pytest

from flytrap.live.api import create_live_app
from flytrap.live.recording import RecordingError
from scripts.sg01_preview import SafeReplayStore, preview_service, safe_capture


def test_sg01_explicit_synthetic_preview_and_inference_guard(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("SG01 art review must not spawn a model or desktop capture")
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    service = preview_service(tmp_path, tmp_path / "no-recordings")
    with TestClient(create_live_app(dist=tmp_path, service=service), base_url="http://127.0.0.1") as client:
        assert client.get("/api/live/status").json()["current"] is None
        assert client.get("/api/live/replays").json()["recordings"] == []
        sources = client.get("/api/live/sources").json()["sources"]
        assert [(s["source_id"], s["evidence_kind"]) for s in sources] == [("fixture-pattern", "fixture")]
        token = client.get("/api/live/control").json()["csrf_token"]
        headers = {"Origin": "http://127.0.0.1", "x-live-csrf": token}
        body = {"request_id": "a" * 32, "owner_token": "b" * 32, "source_id": "fixture-pattern"}
        assert client.post("/api/live/preview", json=body, headers={**headers, "Origin": "http://foreign.invalid"}).status_code == 403
        response = client.post("/api/live/preview", json=body, headers=headers)
        assert response.status_code == 200, response.text
        session_id = response.json()["status"]["session_id"]
        for _ in range(30):
            preview = client.get(f"/api/live/sessions/{session_id}/preview").json()
            if preview["latest"] is not None:
                break
            time.sleep(.01)
        assert preview["latest"] is not None
        stop = {"generation": 1, "owner_token": "b" * 32}
        assert client.post(f"/api/live/sessions/{session_id}/stop", json=stop, headers=headers).status_code == 200
        for _ in range(100):
            if service.snapshot(session_id).status.state == "stopped":
                break
            time.sleep(.01)
        assert service.snapshot(session_id).status.state == "stopped"
        start = {"request_id": "d" * 32, "owner_token": "b" * 32,
                 "config": {"source_id": "fixture-pattern", "evidence_kind": "fixture", "seed": 1},
                 "recording_consent": False}
        response = client.post("/api/live/sessions", json=start, headers=headers)
        assert response.status_code == 503
        assert "no inference" in response.json()["detail"]
    assert not list(tmp_path.rglob("attempts.jsonl"))


def test_sg01_replay_and_capture_allowlists(tmp_path):
    with pytest.raises(RecordingError, match="allowlisted"):
        SafeReplayStore(tmp_path).read("a" * 32)
    from flytrap.live.service import Unavailable
    with pytest.raises(Unavailable, match="synthetic"):
        safe_capture(source_id="/dev/video0")
