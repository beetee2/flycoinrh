"""Launcher ownership and real loopback proxy checks; fixture inputs only."""
from contextlib import contextmanager
import signal
import socket
import subprocess
import time

import httpx
import pytest

from scripts import sg01_dev


def unused_ports():
    with socket.socket() as first, socket.socket() as second:
        first.bind(("127.0.0.1", 0))
        second.bind(("127.0.0.1", 0))
        return first.getsockname()[1], second.getsockname()[1]


def test_live_profile_uses_normal_metadata_and_human_neural_path(monkeypatch):
    from flytrap.live import service, session
    marker = object()
    metadata_calls = []
    monkeypatch.setattr(service, "source_metadata", lambda: metadata_calls.append(True) or [])
    calls = []
    monkeypatch.setattr(session, "NeuralSession", lambda config, **kwargs: calls.append((config, kwargs)) or marker)
    with sg01_dev.profile_service("live") as live:
        assert live.current_id is None and live.sessions == {}
        assert calls == metadata_calls == []
        assert live.execution_purpose == "human"
        assert live.sources().sources == [] and metadata_calls == [True]
        assert live.session_factory("fixture-config", repository_root="fixture-root", source="fixture-source",
            expected_device=None, recording_store=None) is marker
        assert calls == [("fixture-config", dict(purpose="human", repository_root="fixture-root",
            expected_device=None, recording_store=None, source="fixture-source"))]


@pytest.mark.parametrize("conflict", ["api", "frontend"])
def test_port_conflicts_preserve_listener_and_spawn_nothing(monkeypatch, conflict):
    with sg01_dev.reserve_port(0) as occupied:
        busy_port = occupied.getsockname()[1]
        other, _ = unused_ports()
        monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: pytest.fail("must fail before spawn"))
        with pytest.raises(RuntimeError, match=f"Port {busy_port} is unavailable"):
            sg01_dev.run("review", busy_port if conflict == "api" else other,
                         busy_port if conflict == "frontend" else other)
        # The unrelated listener remains alive and usable.
        with socket.create_connection(("127.0.0.1", busy_port), timeout=.5):
            connection, _ = occupied.accept()
            connection.close()
        with sg01_dev.reserve_port(other):
            pass


@pytest.mark.parametrize("failure", ["readiness", "frontend_spawn", "frontend_exit"])
def test_partial_startup_failure_cleans_owned_backend(monkeypatch, failure):
    api_port, ui_port = unused_ports()
    original_popen = subprocess.Popen
    original_stop = sg01_dev.stop_owned
    children = []

    def stop(child):
        assert signal.getsignal(signal.SIGTERM) == signal.SIG_IGN
        assert signal.getsignal(signal.SIGINT) == signal.SIG_IGN
        original_stop(child)

    monkeypatch.setattr(sg01_dev, "stop_owned", stop)

    def popen(command, **kwargs):
        if children and failure == "frontend_spawn":
            raise FileNotFoundError("fixture missing npm")
        if children and failure == "frontend_exit":
            command = [sg01_dev.sys.executable, "-c", "raise SystemExit(7)"]
        child = original_popen(command, **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(subprocess, "Popen", popen)
    if failure == "readiness":
        def fail_ready(*args):
            raise RuntimeError("fixture readiness failure")
        monkeypatch.setattr(sg01_dev, "wait_api", fail_ready)
    if failure == "frontend_exit":
        assert sg01_dev.run("review", api_port, ui_port) == 7
    else:
        with pytest.raises((RuntimeError, FileNotFoundError)):
            sg01_dev.run("review", api_port, ui_port)
    assert children and all(child.poll() is not None for child in children)
    with sg01_dev.reserve_port(api_port), sg01_dev.reserve_port(ui_port):
        pass


@contextmanager
def launched(profile, tmp_path):
    api_port, ui_port = unused_ports()
    script = "dev_sg01.sh" if profile == "review" else "dev_sg01_live.sh"
    with (tmp_path / f"{profile}.log").open("w+") as log:
        sentinel = subprocess.Popen([sg01_dev.sys.executable, "-c", "import time; time.sleep(60)"],
                                    start_new_session=True)
        process = subprocess.Popen([str(sg01_dev.ROOT / "scripts" / script),
            "--api-port", str(api_port), "--ui-port", str(ui_port)], cwd=sg01_dev.ROOT,
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            deadline = time.monotonic() + 15
            with httpx.Client(base_url=f"http://127.0.0.1:{ui_port}", trust_env=False, timeout=.5) as client:
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        log.seek(0)
                        pytest.fail(log.read())
                    try:
                        if client.get("/health/live").status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(.05)
                else:
                    pytest.fail("SG01 fixture launcher did not become ready")
                yield client
        finally:
            if process.poll() is None:
                process.send_signal(signal.SIGTERM)
            try:
                process.wait(timeout=12)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)
                pytest.fail("Launcher failed to stop owned processes")
            finally:
                sentinel_alive = sentinel.poll() is None
                sentinel.terminate()
                sentinel.wait(timeout=3)
            assert sentinel_alive, "Launcher must leave unrelated processes alive"
        # Both backend and Vite are stopped, including npm's child process.
        with sg01_dev.reserve_port(api_port), sg01_dev.reserve_port(ui_port):
            pass


@pytest.mark.parametrize("profile", ["review", "live"])
def test_actual_launcher_proxy_idle_reload_and_control_origin(profile, tmp_path):
    with launched(profile, tmp_path) as client:
        assert client.get("/live").status_code == 200
        assert client.get("/api/live/status").json()["current"] is None
        capabilities = client.get("/api/live/capabilities").json()
        assert capabilities == {"schema_version": "obs-capabilities-1",
            "profile": "art_review" if profile == "review" else "live",
            "preview": True, "replay": True, "inference": profile == "live"}
        assert client.get("/api/live/config").json()["execution_purpose"] == (
            "automated" if profile == "review" else "human")
        sources = client.get("/api/live/sources").json()["sources"]
        if profile == "review":
            assert [source["source_id"] for source in sources] == ["fixture-pattern"]
        else:
            assert all(source["source_id"] != "fixture-pattern" for source in sources)
        token = client.get("/api/live/control").json()["csrf_token"]
        origin = str(client.base_url).rstrip("/")
        body = {"request_id": "a" * 32, "owner_token": "b" * 32, "source_id": "fixture-pattern"}
        assert client.post("/api/live/preview", json=body).status_code == 403
        assert client.post("/api/live/preview", json=body,
            headers={"origin": origin, "x-live-csrf": "invalid"}).status_code == 403
        assert client.post("/api/live/preview", json=body,
            headers={"origin": "http://foreign.invalid", "x-live-csrf": token}).status_code == 403
        if profile == "review":
            headers = {"origin": origin, "x-live-csrf": token}
            response = client.post("/api/live/preview", json=body, headers=headers)
            assert response.status_code == 200, response.text
            session_id = response.json()["status"]["session_id"]
            path = f"/api/live/sessions/{session_id}/stop"
            assert client.post(path, json={"generation": 1, "owner_token": "c" * 32},
                               headers=headers).status_code == 403
            assert client.post(path, json={"generation": 1, "owner_token": "b" * 32},
                               headers=headers).status_code == 200
        # Reload only reads metadata and the shell; no source is selected or started.
        assert client.get("/live").status_code == 200
        status = client.get("/api/live/status").json()["current"]
        if profile == "live":
            assert status is None
        else:
            assert status["status"]["state"] == "stopped"
            assert status["status"]["attempted_calls"] == 0
