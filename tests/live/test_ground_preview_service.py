"""The operator's synthetic preview cannot select capture or inference."""
import subprocess

from fastapi.testclient import TestClient

from flytrap.live.api import create_live_app
from scripts.live_ground_preview import preview_service


def test_ground_preview_rejects_live_and_capture_start_without_spawning(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("ground preview must not start subprocesses")
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    service = preview_service(tmp_path)
    with TestClient(create_live_app(dist=tmp_path, service=service), base_url="http://127.0.0.1") as client:
        assert client.get("/api/live/sources").json()["sources"] == []
        token = client.get("/api/live/control").json()["csrf_token"]
        headers = {"Origin": "http://127.0.0.1", "x-live-csrf": token}
        preview = client.get("/api/live/flight-preview")
        assert preview.status_code == 200
        assert any(s["ground_contact"] for s in preview.json()["snapshots"])
        for endpoint in ("sessions", "preview"):
            body = {"request_id": "a" * 32, "owner_token": "b" * 32}
            if endpoint == "sessions":
                body["config"] = {"source_id": "fixture-pattern", "evidence_kind": "fixture", "seed": 1}
                body["recording_consent"] = False
            else:
                body["source_id"] = "fixture-pattern"
            response = client.post(f"/api/live/{endpoint}", json=body, headers=headers)
            assert response.status_code == 503, response.text
            assert "source" in response.json()["detail"].lower()
        assert client.get("/api/live/status").json()["current"] is None
        assert client.get("/api/live/config").json()["obs_recording_allowed"] is False
    assert not list(tmp_path.rglob("attempts.jsonl"))
