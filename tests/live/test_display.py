"""SG01 safe generated RGB only: no OBS device, model calls or source persistence."""
import base64
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from io import BytesIO
import threading
import time
import uuid

from PIL import Image
import pytest

from flytrap.live.api_contracts import DisplayFrame
from flytrap.live.capture import LatestFrameSlot
from flytrap.live.display import DisplayBuffer, encode_display
from flytrap.live.encoding import RGBFrame, encode_frame, preview_pair
from flytrap.live.fixture import fixture_frame
from tests.live.test_session_api import api, eventually, owner, path, start_body  # noqa: F401


@pytest.mark.parametrize("width,height,expected", [(1920, 1080, (960, 540)),
    (1080, 1920, (304, 540)), (1200, 1200, (540, 540)), (320, 180, (320, 180))])
def test_full_frame_jpeg_preserves_aspect_without_altering_observation(width, height, expected):
    fixture = fixture_frame(3, "fixture-display", 1)
    identity = fixture.identity.model_copy(update={"width": width, "height": height})
    # Original deterministic colorful texture, kept in memory throughout.
    rgb = (bytes(range(256))*((width*height*3+255)//256))[:width*height*3]
    frame = RGBFrame(identity, rgb)
    before = encode_frame(frame)
    packet = encode_display(frame)
    assert (packet.width, packet.height) == expected
    assert 4 <= packet.encoded_bytes <= 262144
    with Image.open(BytesIO(base64.b64decode(packet.jpeg_base64))) as image:
        assert image.size == expected and image.format == "JPEG"
    assert encode_frame(frame) == before
    assert preview_pair(frame).encoded.u8 == before.u8
    assert frame.rgb is rgb
    DisplayFrame.model_validate_json(packet.model_dump_json())


def test_display_keeps_only_latest_and_never_consumes_neural_slot(monkeypatch):
    slot = LatestFrameSlot("fixture-pattern", "fixture-display", 1)
    buffer = DisplayBuffer()
    first = fixture_frame(0, "fixture-display", 1, receipt_monotonic_ms=time.monotonic()*1000)
    assert slot.put(first)
    packet = buffer.get(slot)
    assert packet.frame.sequence == 0
    assert slot.take() is first  # display sampling did not consume the model input
    assert buffer.get(slot) is packet  # separate reference survives neural consumption
    for sequence in range(1, 100):
        assert slot.put(fixture_frame(sequence, "fixture-display", 1, receipt_monotonic_ms=time.monotonic()*1000))
    assert slot.accepted == 100 and slot.latest_preview().identity.sequence == 99
    # More requests cannot increase the encode rate or create queued history.
    for _ in range(100):
        assert buffer.get(slot) is packet
    buffer._next_encode = 0.
    assert buffer.get(slot).frame.sequence == 99
    assert slot.take().identity.sequence == 99
    slot.close()
    assert buffer.get(slot) is None and buffer.latest is None


def test_display_slow_encode_drops_concurrent_requests_and_late_closed_result(monkeypatch):
    import flytrap.live.display as module
    slot = LatestFrameSlot("fixture-pattern", "fixture-display", 1)
    slot.put(fixture_frame(0, "fixture-display", 1, receipt_monotonic_ms=time.monotonic()*1000))
    buffer = DisplayBuffer()
    entered, release = threading.Event(), threading.Event()

    def slow_encode(frame):
        entered.set()
        assert release.wait(2)
        return encode_display(frame)

    monkeypatch.setattr(module, "encode_display", slow_encode)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(buffer.get, slot)
        assert entered.wait(1)
        for sequence in range(1, 100):
            slot.put(fixture_frame(sequence, "fixture-display", 1, receipt_monotonic_ms=time.monotonic()*1000))
            assert buffer.get(slot) is None
        assert buffer.latest is None
        slot.close()
        release.set()
        assert future.result(2) is None
    assert buffer.latest is None


def test_display_rejects_foreign_old_and_expired_frames():
    slot = LatestFrameSlot("fixture-pattern", "fixture-display", 1)
    current = fixture_frame(5, "fixture-display", 1)
    assert slot.put(current)
    for patch in ({"session_id": "foreign"}, {"generation": 2}, {"source_id": "foreign"},
                  {"sequence": 4}):
        assert not slot.put(replace(current, identity=current.identity.model_copy(update=patch)))
    assert slot.latest_preview() is current
    stale = current.identity.model_copy(update={"sequence": 6,
        "receipt_monotonic_ms": time.monotonic()*1000-3000})
    stale_slot = LatestFrameSlot("fixture-pattern", "fixture-display", 1)
    stale_slot.put(replace(current, identity=stale))
    assert DisplayBuffer().get(stale_slot) is None


def test_encoding_failure_clears_color_and_releases_request_lock(monkeypatch, caplog):
    import flytrap.live.display as module
    slot = LatestFrameSlot("fixture-pattern", "fixture-display", 1)
    slot.put(fixture_frame(0, "fixture-display", 1, receipt_monotonic_ms=time.monotonic()*1000))
    buffer = DisplayBuffer()
    assert buffer.get(slot) is not None
    buffer._next_encode = 0.
    slot.put(fixture_frame(1, "fixture-display", 1, receipt_monotonic_ms=time.monotonic()*1000))

    def failed(frame):
        raise ValueError("test source bytes must not be logged")

    monkeypatch.setattr(module, "encode_display", failed)
    assert buffer.get(slot) is None and buffer.latest is None
    assert buffer._next_encode > time.monotonic()
    assert "test source bytes" not in caplog.text
    assert buffer._lock.acquire(blocking=False)
    buffer._lock.release()


def preview(client):
    body = {"request_id": uuid.uuid4().hex, "owner_token": uuid.uuid4().hex,
            "source_id": "fixture-pattern", "duration_seconds": 15}
    response = client.post("/api/live/preview", json=body)
    assert response.status_code == 200, response.text
    return body, response.json()


def test_actual_http_display_requires_owner_origin_generation_and_active_source(api):  # noqa: F811
    client, service, sessions, settings, _ = api
    assert client.get("/api/live/status").json()["current"] is None
    assert client.post("/api/live/sessions/unknown/display", json={
        "owner_token": "1"*32, "generation": 1}).status_code == 404
    assert sessions == [] and settings["captures"] == []
    body, snapshot = preview(client)
    endpoint = path(snapshot, "/display")
    for payload, headers, expected in (
        (owner(body), {"Origin": "https://foreign.example"}, 403),
        (owner(body), {"X-Live-CSRF": "invalid"}, 403),
        ({"owner_token": "3"*32, "generation": 1}, {}, 403),
        (owner(body, 2), {}, 409),
        ({**owner(body), "source_id": "foreign"}, {}, 422),
    ):
        assert client.post(endpoint, json=payload, headers=headers).status_code == expected
    packet = eventually(lambda: client.post(endpoint, json=owner(body)).json()["latest"])
    assert packet["schema_version"] == "screen-gremlin-display-1"
    assert packet["frame"]["session_id"] == snapshot["status"]["session_id"]
    assert packet["frame"]["source_id"] == "fixture-pattern"
    response = client.post(endpoint, json=owner(body))
    assert response.headers["cache-control"] == "no-store"
    assert sessions == [] and len(settings["captures"]) == 1
    assert response.json()["status"]["attempted_calls"] == 0
    assert client.post(path(snapshot, "/stop"), json=owner(body)).status_code == 200
    assert client.post(endpoint, json=owner(body)).json()["latest"] is None
    assert service.entry(snapshot["status"]["session_id"]).display.latest is None
    assert settings["captures"][0].slot.closed


def test_display_requests_do_not_renew_lease_or_change_accounting(api):  # noqa: F811
    client, service, sessions, _, _ = api
    body, snapshot = preview(client)
    entry = service.entry(snapshot["status"]["session_id"])
    lease = entry.session._lease
    for _ in range(8):
        assert client.post(path(snapshot, "/display"), json=owner(body)).status_code == 200
    assert entry.session._lease == lease
    assert sessions == [] and entry.session.status().attempted_calls == 0
    # Exhaust the four simultaneous server slots: fail promptly, without queuing.
    for _ in range(service.max_clients):
        assert service._display_requests.acquire(blocking=False)
    try:
        assert client.post(path(snapshot, "/display"), json=owner(body)).status_code == 429
    finally:
        for _ in range(service.max_clients):
            service._display_requests.release()
    entry.session._lease = time.monotonic()-5
    eventually(lambda: entry.session.wait(0))
    assert client.post(path(snapshot, "/display"), json=owner(body)).json()["latest"] is None
    eventually(lambda: entry.display.latest is None)
    from flytrap.live.accounting import LiveLedger
    assert not LiveLedger.automated(service.root).path.exists()


def test_running_neural_session_display_uses_snapshot_and_preserves_observation_and_flight(api):  # noqa: F811
    """Real NeuralSession coordinator with a labeled no-model subprocess result."""
    from flytrap.live.api_contracts import OwnerRequest
    client, service, sessions, settings, _ = api
    settings["mode"] = "success"  # one fixed synthetic response; no model imports/calls
    body = start_body()
    response = client.post("/api/live/sessions", json=body)
    assert response.status_code == 200
    snapshot = response.json()
    session = sessions[0]
    eventually(lambda: session.snapshot().completed_calls == 1)
    packet = client.post(path(snapshot, "/display"), json=owner(body))
    assert packet.status_code == 200, packet.text
    assert packet.json()["latest"]["frame"]["session_id"] == session.session_id
    assert packet.json()["status"]["state"] == "running"
    eventually(lambda: session._pending is not None)
    # Lock coordinator advancement while comparing the same authoritative instant.
    # Display reads are reentrant and cannot integrate or replace this pending input.
    with session._lock:
        pending = session._pending
        observation = pending.u8
        pose_and_controls = session._flight.current.model_dump()
        inferred = session._inferred.model_dump()
        attempts = session._attempted
        for _ in range(3):
            result = service.display(session.session_id, OwnerRequest(**owner(body)))
            assert result.latest is not None and result.status.state == "running"
        assert session._pending is pending and session._pending.u8 == observation
        assert session._flight.current.model_dump() == pose_and_controls
        assert session._inferred.model_dump() == inferred
        assert session._attempted == attempts
    assert client.post(path(snapshot, "/stop"), json=owner(body)).status_code == 200
    assert client.post(path(snapshot, "/display"), json=owner(body)).json()["latest"] is None
    assert session.wait(1) and session.capture.slot.closed


def test_four_slow_http_transports_bound_response_retention(tmp_path, monkeypatch):
    """Hold actual ASGI body writes: the fifth connection must fail admission."""
    import json
    from fastapi.testclient import TestClient
    from flytrap.live.api import create_live_app
    from flytrap.live.api_contracts import DisplayReply
    from flytrap.live.service import LiveService
    from scripts.live_contract_examples import corpus
    service = LiveService(repository_root=tmp_path, source_provider=lambda: [])
    packet = DisplayReply.model_validate(next(item["value"] for item in corpus()
        if item["contract"] == "DisplayReply" and item["valid"]))
    monkeypatch.setattr(service, "display", lambda *args: packet)
    app = create_live_app(service=service)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        csrf = client.get("/api/live/control").json()["csrf_token"]

    async def verify():
        release = asyncio.Event()
        started = {}
        body = json.dumps({"owner_token": "1"*32, "generation": 1}).encode()

        async def connection(index, disconnect=False):
            received = False

            async def receive():
                nonlocal received
                if not received:
                    received = True
                    return {"type": "http.request", "body": body, "more_body": False}
                await asyncio.Event().wait()

            async def send(message):
                if message["type"] == "http.response.start":
                    started[index] = message["status"]
                    if disconnect:
                        raise ConnectionResetError("Fixture disconnect before body iteration")
                elif message["type"] == "http.response.body" and index < 4:
                    await release.wait()

            scope = {"type": "http", "asgi": {"version": "3.0", "spec_version": "2.4"},
                "method": "POST", "scheme": "http", "path": "/api/live/sessions/fixture/display",
                "raw_path": b"/api/live/sessions/fixture/display", "query_string": b"",
                "root_path": "", "http_version": "1.1", "server": ("127.0.0.1", 80),
                "client": ("127.0.0.1", 10000+index), "headers": [
                    (b"host", b"127.0.0.1"), (b"origin", b"http://127.0.0.1"),
                    (b"content-type", b"application/json"), (b"x-live-csrf", csrf.encode()),
                    (b"cookie", f"live_csrf={csrf}".encode())]}
            await app(scope, receive, send)

        tasks = [asyncio.create_task(connection(index)) for index in range(4)]
        try:
            async with asyncio.timeout(3):
                while len(started) < 4:
                    await asyncio.sleep(.005)
                assert list(started.values()) == [200]*4
                await connection(4)
                assert started[4] == 429
        finally:
            release.set()
            await asyncio.gather(*tasks)
        await connection(5)
        assert started[5] == 200  # all admissions released after response completion
        for index in range(6, 10):
            with pytest.raises(ConnectionResetError):
                await connection(index, disconnect=True)
        await connection(10)
        assert started[10] == 200  # pre-body disconnects must also release admission

    asyncio.run(verify())
