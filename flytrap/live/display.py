"""Capacity-one ephemeral JPEG presentation of the existing capture reader.

Demand driven, at most 15 encodes/second. Slow consumers sample the latest RGB
reference, never a queue. This module has no model, encoder or recording access.
"""
import base64
from io import BytesIO
import threading
import time

from PIL import Image

from .api_contracts import DisplayFrame

MAX_ENCODED_BYTES = 262144
MAX_FPS = 15


def encode_display(frame):
    image = Image.frombytes("RGB", (frame.identity.width, frame.identity.height), frame.rgb)
    try:
        image.thumbnail((960, 540), Image.Resampling.LANCZOS)
        # Bounded worst-case noise uses a lower quality, never an oversized packet.
        for quality in (85, 70, 50, 30):
            with BytesIO() as output:
                image.save(output, format="JPEG", quality=quality, optimize=False)
                jpeg = output.getvalue()
            if len(jpeg) <= MAX_ENCODED_BYTES:
                now = time.monotonic()*1000
                return DisplayFrame(frame=frame.identity, width=image.width, height=image.height,
                    jpeg_base64=base64.b64encode(jpeg).decode("ascii"), encoded_bytes=len(jpeg),
                    delivered_monotonic_ms=now,
                    receipt_age_ms=max(0., now-frame.identity.receipt_monotonic_ms))
        return None
    finally:
        image.close()


class DisplayBuffer:
    def __init__(self):
        self._lock = threading.Lock()
        self.latest = None
        self._next_encode = 0.

    def clear(self):
        with self._lock:
            self.latest = None
            self._next_encode = 0.

    def get(self, slot):
        # A concurrent request never waits in an encoding backlog.
        if not self._lock.acquire(blocking=False):
            return None
        try:
            frame = slot.latest_preview()
            if frame is None or slot.closed:
                self.latest = None
                return None
            if time.monotonic()*1000-frame.identity.receipt_monotonic_ms >= 2000:
                self.latest = None
                return None
            if time.monotonic() < self._next_encode:
                return self.latest
            if self.latest is not None and self.latest.frame == frame.identity:
                return self.latest
            try:
                packet = encode_display(frame)
            except (OSError, ValueError):
                # Never include image bytes or exception payloads in a response/log.
                packet = None
            finally:
                # Completion schedules the next sample; no catch-up after overload.
                self._next_encode = time.monotonic() + 1/MAX_FPS
            self.latest = None if slot.closed else packet
            return self.latest
        finally:
            self._lock.release()
