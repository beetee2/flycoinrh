"""Actual loopback HTTP and synthetic process boundaries for OBS04.

The subprocess fault helper emits labeled synthetic responses and never imports
a model. Capture is a generated RGB fixture, with no device or desktop access.
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import json
import fcntl
import socket
import subprocess
import sys
import threading
import time
import uuid

import httpx
import pytest
import uvicorn

from flytrap.live.accounting import LiveOwnership
from flytrap.live.api import create_live_app
from flytrap.live.contracts import SourceCapability
from flytrap.live.session import NeuralSession
from tests.controllers import conftest as synthetic_fixtures
from tests.live.session_fault_worker import SyntheticCapture

adapter_files = synthetic_fixtures.adapter_files
adapter_files_factory = synthetic_fixtures.adapter_files_factory


def eventually(predicate, timeout=4):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(.01)
    raise AssertionError("condition did not become true within the test deadline")


@contextmanager
def serve(app):
    """Use a real TCP socket and ASGI lifespan, including bounded teardown."""
    sock = socket.socket()
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
    sock.bind(("127.0.0.1", 0))
    sock.listen(128)
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", lifespan="on",
        timeout_graceful_shutdown=1))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    try:
        eventually(lambda: server.started)
        with httpx.Client(base_url=f"http://127.0.0.1:{sock.getsockname()[1]}", timeout=3) as client:
            yield client, server
    finally:
        server.should_exit = True
        thread.join(5)
        sock.close()
        assert not thread.is_alive(), "HTTP lifespan left a server thread alive"


def sse_event(lines):
    for line in lines:
        if line.startswith("data: "):
            return json.loads(line[6:])
    raise AssertionError("stream closed without a current snapshot")


@pytest.fixture
def api(tmp_path):
    from flytrap.live.service import LiveService

    sessions = []
    settings = {"mode": "step_hang", "captures": []}
    source = SourceCapability(schema_version="obs-source-1", source_id="fixture-pattern",
        evidence_kind="fixture", name="Synthetic HTTP fixture", driver=None, backend="synthetic",
        capabilities=None, formats=None, metadata_state="available", producer_detection="synthetic")

    def factory(config, **kwargs):
        recording_kwargs = {key: kwargs[key] for key in ("recording_store", "source") if key in kwargs}
        session = NeuralSession(config, purpose="fixture", repository_root=tmp_path,
            files=settings.get("files", {"allow_fixture": True}), capture_factory=SyntheticCapture,
            worker_command=(None if settings["mode"] == "adapter" else
                [sys.executable, "-m", "tests.live.session_fault_worker", settings["mode"]]),
            **recording_kwargs)
        sessions.append(session)
        return session

    def capture_factory(**kwargs):
        capture = settings.get("capture_type", SyntheticCapture)(**kwargs)
        settings["captures"].append(capture)
        return capture

    service = LiveService(repository_root=tmp_path, session_factory=factory,
        source_provider=lambda: [source], capture_factory=capture_factory)
    with serve(create_live_app(dist=tmp_path / "dist", service=service)) as (client, server):
        csrf = client.get("/api/live/control")
        assert csrf.status_code == 200
        client.headers.update({"Origin": str(client.base_url).rstrip("/"),
                               "X-Live-CSRF": csrf.json()["csrf_token"]})
        yield client, service, sessions, settings, server
    for session in sessions:
        assert session.wait(2), "ASGI shutdown did not end the neural session"
        assert session._child is None or session._child.poll() is not None
        assert session.capture.slot.closed or session.capture.thread is None
        assert session.capture.thread is None or not session.capture.thread.is_alive()
    for capture in settings["captures"]:
        assert capture.slot.closed
        assert capture.thread is None or not capture.thread.is_alive()
    with LiveOwnership(tmp_path):
        pass


def start_body(**config):
    return {"request_id": uuid.uuid4().hex, "owner_token": uuid.uuid4().hex,
        "config": {"source_id": "fixture-pattern", "evidence_kind": "fixture", "seed": 17,
                   "startup_deadline_ms": 2000, "step_deadline_ms": 5000,
                   "stop_grace_ms": 1000, **config}}


def start(client, body):
    response = client.post("/api/live/sessions", json=body)
    assert response.status_code in (200, 201), response.text
    return response.json()


def path(snapshot, suffix=""):
    return f"/api/live/sessions/{snapshot['status']['session_id']}{suffix}"


def owner(body, generation=1):
    return {"owner_token": body["owner_token"], "generation": generation}


def test_actual_http_idle_reads_and_security_cannot_start_work(api):
    client, service, sessions, _, _ = api
    for endpoint in ("/health/live", "/api/live/status", "/api/live/sources"):
        assert client.get(endpoint).status_code == 200
    assert client.get("/api/live/status").json()["current"] is None
    assert client.get("/api/live/sources").json()["sources"][0]["evidence_kind"] == "fixture"
    assert client.get("/health/live", headers={"Host": "evil.example"}).status_code == 400
    body = start_body()
    for headers in ({"Origin": "https://evil.example"}, {"Origin": "null"},
                    {"X-Live-CSRF": "incorrect"}):
        assert client.post("/api/live/sessions", json=body, headers=headers).status_code == 403
    without_origin = dict(client.headers)
    without_origin.pop("origin", None)
    request = httpx.Request("POST", str(client.base_url) + "/api/live/sessions",
                            headers=without_origin, json=body)
    assert client.send(request).status_code == 403
    assert client.post("/api/live/sessions", content=b"x" * 100_000,
                       headers={"Content-Type": "application/json"}).status_code == 413
    chunks = (b"x" * 10_000 for _ in range(10))
    assert client.post("/api/live/sessions", content=chunks,
                       headers={"Content-Type": "application/json"}).status_code == 413
    assert client.post("/api/live/sessions", content=b"{}",
                       headers={"Content-Type": "text/plain"}).status_code == 415
    for invalid in ({**body, "command": "capture"},
                    {**body, "config": {**body["config"], "source_id": "/dev/video0"}},
                    {**body, "config": {**body["config"], "learning_enabled": True}},
                    {**body, "config": {**body["config"], "recording": True}}):
        assert client.post("/api/live/sessions", json=invalid).status_code in (400, 422)
    assert sessions == []
    assert service.stream_stats()["clients"] == 0


def test_blocked_worker_health_owner_idempotence_epoch_and_stop(api, tmp_path):
    client, _, sessions, _, _ = api
    body = start_body()
    snapshot = start(client, body)
    session = sessions[0]
    eventually(lambda: session.snapshot().status.attempted_calls == 1)
    assert session.snapshot().waiting_for_sample
    began = time.monotonic()
    assert client.get("/health/live").status_code == 200
    assert time.monotonic() - began < 1
    assert start(client, body)["status"]["session_id"] == session.session_id
    assert len(sessions) == 1
    assert client.post("/api/live/sessions", json=start_body()).status_code == 409
    changed = {**body, "config": {**body["config"], "seed": 18}}
    assert client.post("/api/live/sessions", json=changed).status_code == 409
    for action in ("renew", "stop"):
        endpoint = path(snapshot, f"/{action}")
        assert client.post(endpoint, json={"owner_token": uuid.uuid4().hex,
                                          "generation": 1}).status_code == 403
        assert client.post(endpoint, json=owner(body, 2)).status_code == 409
    assert client.post(path(snapshot, "/renew"), json=owner(body)).status_code == 200
    with (tmp_path / "artifacts/milestones/P00/model.lock").open("rb") as lock:
        with pytest.raises(BlockingIOError):
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    began = time.monotonic()
    assert client.post(path(snapshot, "/stop"), json=owner(body)).status_code == 200
    assert time.monotonic() - began < 1.5
    eventually(lambda: session.wait(0))
    final = client.get(path(snapshot)).json()
    assert final["status"]["state"] == "stopped"
    assert final["flight"]["neutral"]
    assert final["flight"]["speed_units_s"] == 0
    assert client.post(path(snapshot, "/stop"), json=owner(body)).status_code == 200
    assert start(client, body)["status"]["state"] == "stopped"
    assert len(sessions) == 1


def test_concurrent_http_start_has_exactly_one_owner_and_worker(api):
    client, _, sessions, _, _ = api
    bodies = [start_body() for _ in range(6)]
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda body: client.post("/api/live/sessions", json=body), bodies))
    winners = [response for response in results if response.status_code in (200, 201)]
    assert len(winners) == 1
    assert [response.status_code for response in results].count(409) == 5
    assert len(sessions) == 1
    eventually(lambda: sessions[0]._child is not None)
    assert sessions[0]._child.poll() is None


def test_concurrent_retries_share_one_session_and_cannot_revive_terminal_work(api):
    client, _, sessions, _, _ = api
    body = start_body()
    with ThreadPoolExecutor(max_workers=5) as pool:
        responses = list(pool.map(lambda _: client.post("/api/live/sessions", json=body), range(5)))
    assert all(response.status_code in (200, 201) for response in responses)
    session_ids = {response.json()["status"]["session_id"] for response in responses}
    assert len(session_ids) == len(sessions) == 1
    snapshot = responses[0].json()
    assert client.post(path(snapshot, "/stop"), json=owner(body)).status_code == 200
    replacement_body = start_body()
    replacement = start(client, replacement_body)
    assert replacement["status"]["session_id"] not in session_ids
    old_retry = start(client, body)
    assert old_retry["status"]["session_id"] in session_ids
    assert old_retry["status"]["state"] == "stopped"
    assert client.get("/api/live/status").json()["current"]["status"]["session_id"] == (
        replacement["status"]["session_id"])
    assert len(sessions) == 2


def test_missing_lease_renewals_expire_despite_spectators_and_reconnect(api):
    client, _, sessions, _, _ = api
    body = start_body(lease_ms=600)
    snapshot = start(client, body)
    with client.stream("GET", path(snapshot, "/events"), params={"generation": 1}) as response:
        assert response.status_code == 200
        lines = response.iter_lines()
        first = sse_event(lines)
        assert first["status"]["session_id"] == snapshot["status"]["session_id"]
        eventually(lambda: client.get(path(snapshot)).json()["status"]["state"] == "stopped", timeout=2)
        assert sessions[0].wait(1)
        final = client.get(path(snapshot)).json()
        assert "lease expired" in final["status"]["reason"].lower()
        assert final["lease_remaining_ms"] == 0
    assert client.post(path(snapshot, "/renew"), json=owner(body)).status_code == 409
    with client.stream("GET", path(snapshot, "/events"), params={"generation": 1},
                       headers={"Last-Event-ID": "foreign:999:999999"}) as response:
        current = sse_event(response.iter_lines())
        assert current["status"]["state"] == "stopped"
        assert current["event_sequence"] >= final["event_sequence"]
    assert len(sessions) == 1


def test_stream_disconnect_reconnect_client_cap_and_bounded_backpressure(api):
    from contextlib import ExitStack

    client, service, sessions, settings, _ = api
    settings["mode"] = "normal"
    body = start_body()
    snapshot = start(client, body)
    eventually(lambda: sessions[0].snapshot().completed_calls == 1)
    endpoint = path(snapshot, "/events")
    assert client.get(endpoint, params={"generation": 2}).status_code == 409
    with ExitStack() as stack:
        streams = [stack.enter_context(client.stream("GET", endpoint, params={"generation": 1}))
                   for _ in range(service.max_clients)]
        assert all(response.status_code == 200 for response in streams)
        with client.stream("GET", endpoint, params={"generation": 1}) as rejected:
            assert rejected.status_code == 429
        lines = streams[0].iter_lines()
        first = sse_event(lines)
        start_tick = first["flight"]["tick"]
        # Other sockets intentionally do not consume events. Authority and capture
        # must still advance, with no retained historical queue per subscriber.
        eventually(lambda: client.get(path(snapshot)).json()["flight"]["tick"] > start_tick + 15)
        stats = service.stream_stats()
        assert stats["clients"] == service.max_clients
        assert stats["max_queue"] <= 1
        assert client.post(path(snapshot, "/renew"), json=owner(body)).status_code == 200
        latest = client.get(path(snapshot)).json()
        assert latest["latest_source_frame"]["sequence"] > latest["neural_sample"]["frame"]["sequence"]
    eventually(lambda: service.stream_stats()["clients"] == 0)
    with client.stream("GET", endpoint, params={"generation": 1},
                       headers={"Last-Event-ID": "outdated:1:0"}) as response:
        current = sse_event(response.iter_lines())
        assert current["event_sequence"] >= latest["event_sequence"]
        assert current["flight"]["tick"] >= latest["flight"]["tick"]
        assert current["status"]["session_id"] == snapshot["status"]["session_id"]
    assert len(sessions) == 1


def test_http_lifespan_shutdown_reaps_blocked_worker_and_source(api):
    client, _, sessions, _, server = api
    start(client, start_body())
    eventually(lambda: sessions[0].snapshot().waiting_for_sample)
    child = sessions[0]._child
    assert child.poll() is None
    server.should_exit = True
    eventually(lambda: sessions[0].wait(0))
    assert child.poll() is not None
    assert sessions[0].capture.slot.closed
    assert not sessions[0].capture.thread.is_alive()


def test_sse_open_waiting_for_session_lock_keeps_http_health_responsive(api, monkeypatch):
    client, service, sessions, _, _ = api
    snapshot = start(client, start_body())
    session = sessions[0]
    eventually(lambda: session.snapshot().waiting_for_sample)
    snapshot_entered = threading.Event()
    original = service.snapshot

    def observed_snapshot(session_id):
        snapshot_entered.set()
        return original(session_id)

    monkeypatch.setattr(service, "snapshot", observed_snapshot)

    def connect():
        with client.stream("GET", path(snapshot, "/events"), params={"generation": 1}) as response:
            assert response.status_code == 200
            return sse_event(response.iter_lines())

    with ThreadPoolExecutor(max_workers=1) as pool:
        with session._lock:
            stream = pool.submit(connect)
            assert snapshot_entered.wait(1)
            assert not stream.done()
            began = time.monotonic()
            assert client.get("/health/live", timeout=.5).status_code == 200
            assert time.monotonic() - began < .5
        assert stream.result(timeout=2)["status"]["session_id"] == session.session_id


def test_recording_cap_too_small_fails_before_capture_or_model_start(api):
    client, _, sessions, settings, _ = api
    body = start_body(recording=True, recording_max_bytes=1)
    body["recording_consent"] = True
    response = client.post("/api/live/sessions", json=body)
    assert response.status_code == 422, response.text
    assert settings["captures"] == []
    assert all(session._child is None and session.capture.thread is None
               and session.capture.slot.accepted == 0 for session in sessions)
    assert client.get("/api/live/status").json()["current"] is None


def test_explicit_http_preview_captures_only_fixture_and_closes_on_stop(api):
    client, _, sessions, settings, _ = api
    assert settings["captures"] == []
    body = {"request_id": uuid.uuid4().hex, "owner_token": uuid.uuid4().hex,
            "source_id": "fixture-pattern", "duration_seconds": 1}
    response = client.post("/api/live/preview", json=body)
    assert response.status_code in (200, 201), response.text
    snapshot = response.json()
    assert snapshot["kind"] == "preview"
    assert sessions == []
    assert len(settings["captures"]) == 1
    capture = settings["captures"][0]
    eventually(lambda: capture.slot.accepted > 0)
    preview = client.get(path(snapshot, "/preview")).json()
    assert preview["latest"]["frame"]["evidence_kind"] == "fixture"
    assert len(preview["latest"]["observation_u8"]) == 256
    assert client.post("/api/live/preview", json=body).json()["status"]["session_id"] == (
        snapshot["status"]["session_id"])
    assert len(settings["captures"]) == 1
    assert client.post("/api/live/sessions", json=start_body()).status_code == 409
    # The preview expires itself even if its synthetic producer ignores duration.
    eventually(lambda: capture.slot.closed, timeout=2)
    assert client.get(path(snapshot)).json()["status"]["state"] == "stopped"
    assert client.post(path(snapshot, "/stop"), json=owner(body)).status_code == 200
    assert client.get(path(snapshot, "/preview")).status_code == 200
    assert len(settings["captures"]) == 1 and sessions == []


def test_unread_http_socket_drops_old_events_without_blocking_authority(api):
    client, service, sessions, settings, _ = api
    settings["mode"] = "normal"
    body = start_body()
    snapshot = start(client, body)
    eventually(lambda: sessions[0].snapshot().completed_calls == 1)
    with socket.socket() as slow:
        slow.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024)
        slow.connect((client.base_url.host, client.base_url.port))
        request = (f"GET {path(snapshot, '/events')}?generation=1 HTTP/1.1\r\n"
                   f"Host: {client.base_url.host}:{client.base_url.port}\r\n\r\n")
        slow.sendall(request.encode())
        # Never read even the HTTP headers: eventually the real transport blocks.
        def dropped_while_owner_alive():
            renewal = client.post(path(snapshot, "/renew"), json=owner(body))
            assert renewal.status_code == 200
            return service.stream_stats()["dropped"] > 0
        eventually(dropped_while_owner_alive, timeout=4)
        stats = service.stream_stats()
        assert stats["max_queue"] <= 1
        assert sessions[0].capture.slot.accepted > 10
        assert client.get("/health/live").status_code == 200
    eventually(lambda: service.stream_stats()["clients"] == 0)


def test_preview_failed_capture_cleanup_retains_exclusion_until_reader_closes(api, tmp_path):
    class ReturningStopCapture(SyntheticCapture):
        def stop(self):
            # A backend returning from failed cleanup cannot attest reader closure.
            self.state = "failed"

    client, _, sessions, settings, _ = api
    settings["capture_type"] = ReturningStopCapture
    body = {"request_id": uuid.uuid4().hex, "owner_token": uuid.uuid4().hex,
            "source_id": "fixture-pattern", "duration_seconds": 1}
    response = client.post("/api/live/preview", json=body)
    assert response.status_code == 200, response.text
    capture = settings["captures"][0]
    try:
        eventually(lambda: capture.state == "failed", timeout=2)
        # Exercise the existing 3-second shutdown bound. The caller may finish
        # waiting; ownership must remain until the actual source reader closes.
        deadline = time.monotonic() + 3.3
        while time.monotonic() < deadline:
            assert client.get("/health/live").status_code == 200
            time.sleep(.05)
        assert capture.thread.is_alive()
        from flytrap.live.accounting import BusyError
        with pytest.raises(BusyError):
            with LiveOwnership(tmp_path):
                pass
        assert client.post("/api/live/sessions", json=start_body()).status_code == 409
        assert sessions == []
    finally:
        SyntheticCapture.stop(capture)


def test_opt_in_recording_http_replay_preserves_ledger_and_source_handles(api, adapter_files, tmp_path,
                                                                        monkeypatch):
    from flytrap.live.accounting import LiveLedger
    from flytrap.controllers.fly import FlyController
    from flytrap.live.capture import Capture

    client, service, sessions, settings, _ = api
    settings.update(mode="adapter", files=adapter_files)
    body = start_body(recording=True, max_model_calls=2, duration_seconds=8, startup_deadline_ms=5000)
    body["recording_consent"] = True
    initial = start(client, body)

    def completed():
        current = client.get(path(initial)).json()
        if current["status"]["state"] in {"failed", "stopped", "limit_reached"}:
            return current
        assert client.post(path(initial, "/renew"), json=owner(body)).status_code in (200, 409)
        return None

    final = eventually(completed, timeout=8)
    assert final["status"]["state"] == "limit_reached", final
    assert sessions[0].wait(2)
    eventually(lambda: client.get(path(initial)).json()["recording_state"] != "partial", timeout=2)
    final = client.get(path(initial)).json()
    assert final["recording_state"] == "complete"
    recording_id = final["recording_id"]
    assert recording_id
    ledger = LiveLedger.session(tmp_path, sessions[0].session_id, cap=2, mode="automated")
    assert ledger.attempted == 2
    artifacts = tmp_path / "artifacts"
    before = {str(file.relative_to(artifacts)): file.read_bytes()
              for file in artifacts.rglob("*") if file.is_file()}

    def forbidden(*args, **kwargs):
        raise AssertionError("ordinary replay attempted capture or neural work")

    monkeypatch.setattr(Capture, "start", forbidden)
    monkeypatch.setattr(SyntheticCapture, "start", forbidden)
    monkeypatch.setattr(FlyController, "__init__", forbidden)
    monkeypatch.setattr(LiveLedger, "record_attempt", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    response = client.get(f"/api/live/replays/{recording_id}")
    assert response.status_code == 200, response.text
    replay = response.json()
    assert replay["manifest"]["state"] == "complete"
    assert replay["manifest"]["evidence_kind"] == "fixture"
    assert len(replay["inputs"]) == len(replay["samples"]) == 2
    assert all(len(sample["observation_u8"]) == 256 for sample in replay["samples"])
    listed = client.get("/api/live/replays")
    assert listed.status_code == 200 and recording_id in listed.text
    for tick in (0, final["flight"]["tick"]):
        state = client.get(f"/api/live/replays/{recording_id}/seek", params={"tick": tick})
        assert state.status_code == 200, state.text
        assert state.json()["snapshot"]["tick"] == tick
    assert client.get(f"/api/live/replays/{recording_id}/seek", params={"tick": -1}).status_code in (400, 422)
    assert client.get(f"/api/live/replays/{recording_id}/seek", params={"tick": 999999}).status_code in (400, 422)
    after = {str(file.relative_to(artifacts)): file.read_bytes()
             for file in artifacts.rglob("*") if file.is_file()}
    assert after == before
    assert len(sessions) == 1 and sessions[0].capture.slot.closed
    assert ledger.attempted == 2
    assert not (artifacts / "live/validation/attempts.jsonl").exists()
