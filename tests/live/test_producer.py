"""Synthetic local websocket peer; never connects to OBS or a capture device."""
from contextlib import contextmanager
import json
import logging
import threading
import time

import pytest
from websockets.exceptions import ConnectionClosed
from websockets.sync.server import serve

from flytrap.live import producer
from flytrap.live.producer import ObsProducerMonitor


PASSWORD = "supersecretpassword"  # Published OBS protocol example, fixture only.
SALT = "lM1GncleQOaCu9lT1yeUZhFYnqhsLLP1G5lAGo3ixaI="
CHALLENGE = "+IxH4CnCiqpX1rM9scsNynZzbOe4KhDeYcTNS3PDaeY="
# Independently computed with OpenSSL's SHA256, then base64 at each stage.
AUTH = "1Ct943GAT+6YQUUX47Ia/ncufilbe6+oD6lY+5kaCu4="


@contextmanager
def obs_peer(mode="active"):
    received = []
    logger = logging.Logger("fixture-private-obs")
    logger.disabled = True

    def handler(socket):
        try:
            if mode == "blocked_hello":
                socket.recv(timeout=1)
                return
            hello = {"rpcVersion": 1, "authentication": {"salt": SALT, "challenge": CHALLENGE}}
            if mode == "no_auth":
                del hello["authentication"]
            if mode == "bad_challenge":
                hello["authentication"]["salt"] = 7
            if mode == "old_protocol":
                hello["rpcVersion"] = 0
            socket.send(json.dumps({"op": 0, "d": hello}))
            identify = json.loads(socket.recv(timeout=1))
            received.append(identify)
            if mode == "auth_failure" or identify.get("d", {}).get("authentication") != AUTH:
                socket.close(4009, PASSWORD)
                return
            socket.send(json.dumps({"op": 2, "d": {"negotiatedRpcVersion": 1}}))
            request = json.loads(socket.recv(timeout=1))
            received.append(request)
            if mode == "blocked_reply":
                socket.recv(timeout=1)
                return
            response = {"requestType": "GetVirtualCamStatus", "requestId": request["d"]["requestId"],
                        "requestStatus": {"result": True, "code": 100},
                        "responseData": {"outputActive": mode != "inactive"}}
            if mode == "wrong_id":
                response["requestId"] = "old-response"
            if mode == "wrong_request":
                response["requestType"] = "GetStreamStatus"
            if mode == "unsupported":
                response["requestStatus"] = {"result": False, "code": 204, "comment": PASSWORD}
            if mode == "integer_active":
                response["responseData"]["outputActive"] = 1
            if mode == "integer_success":
                response["requestStatus"]["result"] = 1
            if mode == "bad_json":
                socket.send("not-json:" + PASSWORD)
            elif mode == "oversized":
                socket.send("x" * (producer.MAX_MESSAGE_BYTES + 1))
            elif mode == "binary":
                socket.send(json.dumps({"op": 7, "d": response}).encode())
            elif mode == "unsolicited_event":
                socket.send(json.dumps({"op": 5, "d": {"eventType": "VirtualcamStateChanged"}}))
            else:
                socket.send(json.dumps({"op": 7, "d": response}))
            socket.recv(timeout=1)
        except (ConnectionClosed, TimeoutError):
            pass

    with serve(handler, "127.0.0.1", 0, logger=logger, close_timeout=0.05) as server:
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            yield server.socket.getsockname()[1], received
        finally:
            server.shutdown()
            thread.join(timeout=1)
            assert not thread.is_alive()


@pytest.mark.parametrize("mode", ["active", "inactive"])
def test_authenticated_read_only_status_and_no_plaintext_password(mode, caplog):
    caplog.set_level(logging.DEBUG)
    with obs_peer(mode) as (port, received):
        monitor = ObsProducerMonitor(password=PASSWORD, port=port)
        assert monitor.snapshot().state == "unknown"
        assert not received
        status = monitor.poll()
        assert status.state == mode
        assert status.checked_monotonic_ms is not None
        identify, request = received
        assert identify == {"op": 1, "d": {"rpcVersion": 1, "eventSubscriptions": 0, "authentication": AUTH}}
        assert request["op"] == 6
        assert set(request["d"]) == {"requestType", "requestId"}
        assert request["d"]["requestType"] == "GetVirtualCamStatus"
        assert PASSWORD not in json.dumps(received)
        assert PASSWORD not in repr(monitor) + repr(vars(monitor)) + repr(status) + caplog.text
        assert AUTH not in caplog.text


@pytest.mark.parametrize("mode", ["no_auth", "bad_challenge", "old_protocol", "auth_failure", "wrong_id",
                                 "wrong_request", "unsupported", "integer_active", "integer_success",
                                 "bad_json", "oversized", "binary", "unsolicited_event"])
def test_unknown_on_untrustworthy_or_unsupported_status(mode, caplog):
    caplog.set_level(logging.DEBUG)
    with obs_peer(mode) as (port, _):
        monitor = ObsProducerMonitor(password=PASSWORD, port=port)
        status = monitor.poll()
    assert status.state == "unknown"
    assert status.checked_monotonic_ms is None
    assert status.reason == "authenticated_status_unavailable"
    assert PASSWORD not in repr(status) + caplog.text
    assert AUTH not in caplog.text


@pytest.mark.parametrize("mode", ["blocked_hello", "blocked_reply"])
def test_hung_peer_has_bounded_poll_and_no_old_active_state(mode):
    with obs_peer(mode) as (port, _):
        monitor = ObsProducerMonitor(password=PASSWORD, port=port, timeout_s=0.08)
        monitor._status = producer.ProducerStatus("active", producer._monotonic_ms(), "fixture")
        start = time.monotonic()
        status = monitor.poll()
        elapsed = time.monotonic() - start
    assert status.state == "unknown"
    assert status.reason == "heartbeat_timeout"
    assert elapsed < 0.5
    assert monitor.snapshot().state == "unknown"


def test_successful_heartbeat_expires_without_network_and_static_pixels_irrelevant(monkeypatch):
    with obs_peer() as (port, received):
        monitor = ObsProducerMonitor(password=PASSWORD, port=port, inactivity_s=1)
        status = monitor.poll()
        assert status.state == "active"
        monkeypatch.setattr(producer, "_monotonic_ms", lambda: status.checked_monotonic_ms + 1000)
        assert monitor.snapshot().state == "unknown"
        assert monitor.snapshot().reason == "heartbeat_expired"
        assert len(received) == 2


def test_actual_wrong_password_is_rejected_without_status_request():
    with obs_peer() as (port, received):
        monitor = ObsProducerMonitor(password="incorrect-fixture-password", port=port)
        assert monitor.poll().state == "unknown"
        assert len(received) == 1
        assert received[0]["op"] == 1


def test_connection_settings_cannot_use_proxy_remote_host_or_redirect(monkeypatch):
    seen = []

    def no_network(uri, **kwargs):
        seen.append((uri, kwargs))
        raise OSError(PASSWORD)

    original = producer._LocalConnect
    monkeypatch.setattr(producer, "_LocalConnect", no_network)
    monitor = ObsProducerMonitor(password=PASSWORD, port=4455)
    assert not seen
    assert monitor.poll().state == "unknown"
    uri, options = seen[0]
    assert uri == "ws://127.0.0.1:4455"
    assert options["proxy"] is None
    assert options["max_queue"] == 1
    assert options["max_size"] == producer.MAX_MESSAGE_BYTES
    assert options["logger"].disabled
    redirect = OSError("redirect to remote.invalid")
    assert original.process_redirect(None, redirect) is redirect


@pytest.mark.parametrize("kwargs", [
    {"password": ""}, {"password": "x" * 1025}, {"port": True}, {"port": 80},
    {"port": "4455"}, {"timeout_s": float("nan")}, {"inactivity_s": float("inf")},
    {"timeout_s": 3}, {"inactivity_s": 3}, {"timeout_s": True},
])
def test_invalid_configuration_rejected_before_network(kwargs):
    with pytest.raises(ValueError):
        ObsProducerMonitor(**{"password": PASSWORD, **kwargs})


def test_concurrent_poll_does_not_queue_or_renew_heartbeat():
    monitor = ObsProducerMonitor(password=PASSWORD)
    with monitor._poll_lock:
        status = monitor.poll()
    assert status.state == "unknown" and status.reason == "poll_busy"
    assert status.checked_monotonic_ms is None
