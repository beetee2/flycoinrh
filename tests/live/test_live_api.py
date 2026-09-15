"""Idle lifecycle boundary, with capture/model subprocesses forbidden."""
import subprocess
import sys

import pytest
from fastapi.testclient import TestClient

from flytrap.live.api import create_live_app
from flytrap.live.contracts import LiveConfig, LiveHealth


def test_idle_reads_never_discover_capture_or_infer(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("idle service must not spawn work")
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    with TestClient(create_live_app(dist=tmp_path), base_url="http://127.0.0.1") as client:
        for _ in range(3):
            response = client.get("/health/live")
            assert response.status_code == 200
            assert response.json() == LiveHealth().model_dump()
            assert client.get("/api/live/config").json() == LiveConfig().model_dump()
        assert client.get("/live").status_code == 503
        assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("path", ["/api/live/start", "/api/live/config"])
def test_no_capture_mutations_exposed(path, tmp_path):
    with TestClient(create_live_app(dist=tmp_path), base_url="http://127.0.0.1") as client:
        response = client.post(path, json={"source_id": "/dev/video0"}, headers={"Origin": "https://evil.test"})
        assert response.status_code in (404, 405)
        assert "access-control-allow-origin" not in response.headers


def test_trusted_host_and_asset_scope(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets/app.js").write_text("// approved built asset")
    (tmp_path / "index.html").write_text("<main>OBS00 idle</main>")
    (tmp_path / "private.txt").write_text("must not serve")
    with TestClient(create_live_app(dist=tmp_path), base_url="http://127.0.0.1") as client:
        assert client.get("/health/live", headers={"Host": "evil.test"}).status_code == 400
        assert client.get("/", follow_redirects=False).headers["location"] == "/live"
        assert client.get("/live").text == "<main>OBS00 idle</main>"
        assert client.get("/assets/app.js").status_code == 200
        for path in ("/private.txt", "/assets/%2e%2e/private.txt", "/.env", "/data/body-annotations.feather"):
            assert client.get(path).status_code == 404
        response = client.get("/api/live/config")
        assert response.headers["cache-control"] == "no-store"
        assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_fresh_process_import_has_no_model_or_capture_dependencies():
    script = """
import sys
from flytrap.live.api import create_live_app
create_live_app()
assert not any(name in sys.modules for name in (
    'flysim', 'flyeye', 'flytrap.controllers.fly', 'flytrap.lab.runner', 'flytrap.live.environment'))
"""
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


def test_synthetic_flight_preview_is_bounded_repeatable_and_has_no_side_effects(tmp_path, monkeypatch):
    from flytrap.live.contracts import SyntheticFlightPreview

    def forbidden(*args, **kwargs):
        raise AssertionError("synthetic presentation cannot spawn capture or inference")
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    with TestClient(create_live_app(dist=tmp_path), base_url="http://127.0.0.1") as client:
        response = client.get("/api/live/flight-preview")
        assert response.status_code == 200
        preview = SyntheticFlightPreview.model_validate(response.json())
        assert preview.evidence_kind == "synthetic" and len(preview.snapshots) == 601
        assert preview.snapshots[-1].position != preview.snapshots[0].position
        assert len(response.content) < 400_000
        assert client.get("/api/live/flight-preview").json() == response.json()
        assert list(tmp_path.iterdir()) == []
        assert client.post("/api/live/flight-preview").status_code == 405


def test_explicit_metadata_inspection_is_protected_and_does_not_capture(tmp_path, monkeypatch):
    from flytrap.live import device
    from flytrap.live.contracts import SourceCapability
    from flytrap.live.service import LiveService
    from tests.live.test_device import configuration

    inspected = []
    def inspect(source_id):
        inspected.append(source_id)
        return configuration(keep_format=0)
    monkeypatch.setattr(device, "inspect_selected", inspect)
    source = SourceCapability(schema_version="obs-source-1", source_id="v4l2-video7", evidence_kind="real",
        name="Declared device metadata fixture", driver=None, backend="ffmpeg-v4l2",
        capabilities=None, formats=None, metadata_state="partial", producer_detection="unknown")
    service = LiveService(repository_root=tmp_path, source_provider=lambda: [source])
    with TestClient(create_live_app(dist=tmp_path, service=service), base_url="http://127.0.0.1") as client:
        endpoint = "/api/live/sources/inspect"
        assert client.post(endpoint, json={"source_id": source.source_id}).status_code == 403
        assert inspected == []
        token = client.get("/api/live/control").json()["csrf_token"]
        # A spectator tab bootstrapping the shared browser cookie cannot revoke
        # the owner's CSRF protection; ownership still uses a per-tab secret.
        assert client.get("/api/live/control").json()["csrf_token"] == token
        headers = {"Origin": "http://127.0.0.1", "X-Live-CSRF": token}
        response = client.post(endpoint, headers=headers, json={"source_id": source.source_id})
        assert response.status_code == 200
        metadata = SourceCapability.model_validate(response.json())
        assert metadata.formats[0].pixel_format == "YUYV" and metadata.formats[0].fps == 30
        assert metadata.producer_detection == "driver" and metadata.driver == "v4l2 loopback"
        assert client.post(endpoint, headers=headers, json={"source_id": "/dev/video7"}).status_code == 422
        assert client.post(endpoint, headers=headers, json={"source_id": "v4l2-video8"}).status_code == 503
        assert inspected == [source.source_id] and not service.sessions
        assert list(tmp_path.iterdir()) == []
