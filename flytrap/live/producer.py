"""Authenticated, read-only OBS v5 status polling; no camera or OBS mutations.

Protocol: https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md
An active virtual camera says nothing about the source application's animation.
Call poll() in a worker, never in the API event loop or the frame-draining thread.
"""
import asyncio
from base64 import b64encode
from dataclasses import dataclass
import hashlib
import json
import logging
import math
import threading
import time
from typing import Literal
import uuid

from pydantic import SecretStr
from websockets.asyncio.client import connect


MAX_MESSAGE_BYTES = 8192
# An isolated disabled logger prevents websocket debug frames/auth and remote
# error text from escaping through application/root logging configuration.
_PRIVATE_LOGGER = logging.Logger("flyjam-private-obs-monitor")
_PRIVATE_LOGGER.disabled = True
_PRIVATE_LOGGER.propagate = False


def _monotonic_ms() -> float:
    return time.monotonic() * 1000


class _LocalConnect(connect):
    def process_redirect(self, exc: Exception) -> Exception:
        # websockets normally follows redirects, including off-loopback URLs.
        return exc


@dataclass(frozen=True)
class ProducerStatus:
    state: Literal["active", "inactive", "unknown"] = "unknown"
    checked_monotonic_ms: float | None = None
    reason: str = "not_checked"


class ObsProducerMonitor:
    """Explicit polling only; construction never connects. No secret in repr.

    Each bounded poll authenticates a fresh loopback connection and requests one
    status. This prevents an old queued event/reply from renewing the heartbeat.
    Failure immediately invalidates prior active status. The caller must honor
    snapshot() expiry independently of its next poll.
    """

    def __init__(self, *, password: str, port: int = 4455,
                 timeout_s: float = 0.5, inactivity_s: float = 2.0):
        if type(password) is not str or not 1 <= len(password) <= 1024:
            raise ValueError("OBS password must be supplied privately and have a bounded length")
        if type(port) is not int or not 1024 <= port <= 65535:
            raise ValueError("OBS port must be an unprivileged local port")
        for value in (timeout_s, inactivity_s):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("OBS deadlines must be finite numbers")
        if not 0.01 <= timeout_s <= 1.0 or not timeout_s <= inactivity_s <= 2.0:
            raise ValueError("OBS polling deadline must fit within the two-second heartbeat bound")
        self._password = SecretStr(password)
        self._port = port
        self._timeout_s = timeout_s
        self._inactivity_ms = inactivity_s * 1000
        self._status = ProducerStatus()
        self._poll_lock = threading.Lock()

    def snapshot(self) -> ProducerStatus:
        status = self._status
        if (status.checked_monotonic_ms is not None
                and _monotonic_ms() - status.checked_monotonic_ms >= self._inactivity_ms):
            return ProducerStatus(reason="heartbeat_expired")
        return status

    def poll(self) -> ProducerStatus:
        if not self._poll_lock.acquire(blocking=False):
            return ProducerStatus(reason="poll_busy")
        try:
            try:
                active = asyncio.run(self._bounded_query())
                self._status = ProducerStatus("active" if active else "inactive",
                                              _monotonic_ms(), "authenticated_obs_status")
            except TimeoutError:
                self._status = ProducerStatus(reason="heartbeat_timeout")
            except Exception:
                # Server close reasons, response comments, challenges and auth
                # failures may contain secrets. Never retain/format exceptions.
                self._status = ProducerStatus(reason="authenticated_status_unavailable")
            return self._status
        finally:
            self._poll_lock.release()

    async def _bounded_query(self) -> bool:
        return await asyncio.wait_for(self._query(), timeout=self._timeout_s)

    async def _query(self) -> bool:
        websocket = None
        try:
            websocket = await _LocalConnect(
                f"ws://127.0.0.1:{self._port}", proxy=None, compression=None,
                open_timeout=self._timeout_s, close_timeout=0.05, ping_interval=None,
                max_size=MAX_MESSAGE_BYTES, max_queue=1, write_limit=4096,
                logger=_PRIVATE_LOGGER,
            )

            async def receive(op: int) -> dict:
                raw = await websocket.recv()
                if type(raw) is not str:
                    raise ValueError("invalid protocol")
                message = json.loads(raw)
                if (type(message) is not dict or type(message.get("op")) is not int
                        or message["op"] != op or type(message.get("d")) is not dict):
                    raise ValueError("invalid protocol")
                return message["d"]

            hello = await receive(0)
            auth = hello.get("authentication")
            if (type(hello.get("rpcVersion")) is not int or hello["rpcVersion"] < 1
                    or type(auth) is not dict):
                raise ValueError("authenticated protocol required")
            if any(type(auth.get(key)) is not str or not 1 <= len(auth[key]) <= 256
                   for key in ("salt", "challenge")):
                raise ValueError("invalid authentication challenge")
            secret = b64encode(hashlib.sha256(
                (self._password.get_secret_value() + auth["salt"]).encode("utf-8")
            ).digest()).decode("ascii")
            authentication = b64encode(hashlib.sha256(
                (secret + auth["challenge"]).encode("utf-8")
            ).digest()).decode("ascii")
            await websocket.send(json.dumps({"op": 1, "d": {
                "rpcVersion": 1, "authentication": authentication, "eventSubscriptions": 0,
            }}))
            identified = await receive(2)
            if type(identified.get("negotiatedRpcVersion")) is not int or identified["negotiatedRpcVersion"] != 1:
                raise ValueError("unsupported protocol")
            request_id = uuid.uuid4().hex
            await websocket.send(json.dumps({"op": 6, "d": {
                "requestType": "GetVirtualCamStatus", "requestId": request_id,
            }}))
            response = await receive(7)
            status, data = response.get("requestStatus"), response.get("responseData")
            if (response.get("requestType") != "GetVirtualCamStatus"
                    or response.get("requestId") != request_id or type(status) is not dict
                    or status.get("result") is not True or type(status.get("code")) is not int
                    or status["code"] != 100 or type(data) is not dict
                    or type(data.get("outputActive")) is not bool):
                raise ValueError("invalid status response")
            return data["outputActive"]
        finally:
            if websocket is not None:
                # Abort the owned transport immediately, including on timeout;
                # a remote close handshake cannot extend the polling deadline.
                websocket.transport.abort()
