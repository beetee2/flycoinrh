"""Explicit ephemeral fixture preview over real local HTTP; no capture devices."""
import base64
from contextlib import contextmanager
from hashlib import sha256
import json
from pathlib import Path
import re
import selectors
import socket
import subprocess
import sys
import time

from fastapi.testclient import TestClient
import httpx
import pytest

from flytrap.live import capture, preview
from flytrap.live.__main__ import main
from flytrap.live.api import create_live_app
from flytrap.live.contracts import FrameIdentity
from flytrap.live.encoding import RGBFrame, encode_frame

ROOT = Path(__file__).resolve().parents[2]


def free_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


@contextmanager
def fixture_server(seconds=2.0):
    """Start the maintained explicit CLI and always reap this owned child."""
    port = free_port()
    child = subprocess.Popen(
        [sys.executable, "-m", "flytrap.live", "preview", "--source", "fixture-pattern",
         "--seconds", str(seconds), "--port", str(port)],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(child.stdout, selectors.EVENT_READ)
            assert selector.select(5), "fixture preview did not announce startup within its bound"
            line = child.stdout.readline()
        match = re.fullmatch(r"Preview: (http://127\.0\.0\.1:\d+/preview/[A-Za-z0-9_-]+) .+\n", line)
        assert match, line
        yield child, match.group(1)
    finally:
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=3)
        child.stdout.close()
        child.stderr.close()


def test_capture_constructor_and_harmless_page_do_not_open_sources(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("constructor and idle page reads cannot inspect or open a source")

    monkeypatch.setattr(capture, "inspect_selected", forbidden)
    monkeypatch.setattr(capture.subprocess, "Popen", forbidden)
    source = capture.Capture(source_id="v4l2-video77", session_id="idle-test", generation=1)
    assert source.status().state == "idle" and source.slot.latest() is None
    with TestClient(create_live_app(dist=tmp_path), base_url="http://127.0.0.1") as client:
        for _ in range(2):
            page = client.get("/live/obs-test")
            assert page.status_code == 200
            assert "FIXTURE TEST CONTENT" in page.text
            assert "requestAnimationFrame" in page.text
            assert page.headers["cache-control"] == "no-store"
            assert "default-src 'none'" in page.headers["content-security-policy"]
        assert client.get("/health/live").status_code == 200
    assert source.status().state == "idle"


def test_explicit_fixture_http_identity_pixels_privacy_and_expiry():
    with fixture_server() as (child, url), httpx.Client(timeout=1, trust_env=False) as client:
        page = client.get(url)
        assert page.status_code == 200
        assert "Explicit source preview" in page.text
        assert page.headers["cache-control"] == "no-store"
        assert page.headers["referrer-policy"] == "no-referrer"
        assert "frame-ancestors 'none'" in page.headers["content-security-policy"]
        assert "access-control-allow-origin" not in page.headers
        payload = client.get(url + "/frame").json()
        assert payload["label"] == "SYNTHETIC FIXTURE"
        assert payload["neural_calls"] == 0 and payload["recording"] is False
        assert payload["status"]["state"] == "previewing"
        assert payload["status"]["producer"] == "synthetic"
        assert payload["status"]["verified_live"] is False
        identity = FrameIdentity.model_validate(payload["frame"])
        assert identity.source_id == "fixture-pattern" and identity.evidence_kind == "fixture"
        assert identity.source_sequence is not None
        # Default fixture dimensions fit without resizing, so this cross-boundary
        # oracle proves both HTTP previews describe exactly the same source bytes.
        rgb = base64.b64decode(payload["preview_rgb"], validate=True)
        assert payload["preview_width"] == identity.width == 320
        assert payload["preview_height"] == identity.height == 180
        encoded = encode_frame(RGBFrame(identity, rgb))
        assert payload["observation_u8"] == list(encoded.u8)
        assert payload["observation_sha256"] == encoded.sha256 == sha256(encoded.u8).hexdigest()
        assert client.get(url, headers={"Host": "attacker.example"}).status_code == 403
        assert client.get(url + "/frame", headers={"Origin": "https://attacker.example"}).status_code == 403
        assert client.get(url.rsplit("/", 1)[0] + "/wrong-token/frame").status_code == 404
        assert client.post(url + "/frame").status_code >= 400
        assert client.get(url + "/frame", headers={"Origin": url.split("/preview/")[0]}).status_code == 200
        stdout, stderr = child.communicate(timeout=5)
        assert child.returncode == 0, stderr
        terminal = json.loads(stdout.strip())
        assert terminal["capture"]["state"] in ("limit_reached", "stopped")
        assert terminal["capture"]["accepted_frames"] > 1
        assert terminal["neural_calls"] == 0 and terminal["recording"] is False
        assert stderr == ""  # No private request paths are logged.
        with pytest.raises(httpx.ConnectError):
            client.get(url + "/frame")


def test_expiry_stops_fixture_thread_and_discards_pixels(monkeypatch, capsys):
    instances = []

    class ObservedCapture(capture.Capture):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            instances.append(self)

    monkeypatch.setattr(preview, "Capture", ObservedCapture)
    started = time.monotonic()
    assert preview.run_preview(source_id="fixture-pattern", duration_s=.15, port=free_port()) == 0
    assert time.monotonic() - started < 2
    source, = instances
    assert source.status().state in ("limit_reached", "stopped")
    assert source.slot.closed and source.slot.latest() is None
    assert source._thread is not None and not source._thread.is_alive()
    assert source._child is None
    assert '"neural_calls": 0' in capsys.readouterr().out


def test_port_conflict_never_starts_capture(monkeypatch):
    monkeypatch.setattr(preview.Capture, "start", lambda self: pytest.fail("busy port started capture"))
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        with pytest.raises(OSError):
            preview.run_preview(source_id="fixture-pattern", duration_s=.1, port=port)
        # The unrelated socket remains usable and owned by this test.
        with socket.create_connection(("127.0.0.1", port), timeout=.5):
            accepted, _ = listener.accept()
            accepted.close()


def test_slow_partial_http_headers_cannot_extend_preview_lifetime():
    with fixture_server(.3) as (child, url):
        port = int(url.split(":")[2].split("/")[0])
        with socket.create_connection(("127.0.0.1", port), timeout=.5) as connection:
            start = time.monotonic()
            connection.sendall(b"GET / HTTP/1.1\r\nX-Slow: ")
            while child.poll() is None and time.monotonic() - start < 1.5:
                try:
                    connection.sendall(b"x")
                except OSError:
                    break
                time.sleep(.05)
            stdout, stderr = child.communicate(timeout=1)
            assert child.returncode == 0, stderr
            assert time.monotonic() - start < 1.2
            assert json.loads(stdout)["neural_calls"] == 0


@pytest.mark.parametrize("arguments", [["preview"], ["preview", "--seconds", "1"]])
def test_cli_requires_explicit_source(arguments):
    with pytest.raises(SystemExit) as error:
        main(arguments)
    assert error.value.code == 2


@pytest.mark.parametrize("seconds", ["0", "-1", "31", "nan", "inf"])
def test_cli_rejects_invalid_preview_bounds_without_start(seconds, monkeypatch, capsys):
    monkeypatch.setattr(preview.Capture, "start", lambda self: pytest.fail("invalid duration started capture"))
    assert main(["preview", "--source", "fixture-pattern", "--seconds", seconds]) == 2
    assert "unavailable" in capsys.readouterr().out
