"""Authoritative ``grayscale_v1`` pixels and ``crop16_v1`` observations.

The 96×96 raster has no avatar, text, paths, scoring, or clock information.
Pads use local 8-pixel cells: the first stripe/checker cell is white. Raster
rectangles are half-open. Crops cover a 128-pixel field using 16×16 nearest
cell-center samples: floor(position - 64 + 4 + 8 * index), clipped to [0, 95].
Each raw byte is normalized by Python division by 255. Observation digests
hash the 256 sampled grayscale bytes, not serialized floats or PNG encoding.
"""

from dataclasses import replace
import hashlib
from io import BytesIO

from flytrap.arena.core import Scene
from flytrap.contracts import Observation


RENDERER_VERSION = "grayscale_v1"
CROP_VERSION = "crop16_v1"
RASTER_SIZE = 96


def render(scene: Scene) -> bytes:
    """Render validated visible geometry only, returning 9,216 row-major bytes."""
    if type(scene) is not Scene:
        raise ValueError("renderer requires a Scene")
    scene = replace(scene)  # Revalidate even a frozen instance bypassed by a caller.
    pixels = bytearray([128]) * (RASTER_SIZE * RASTER_SIZE)
    for y in range(RASTER_SIZE):
        for x in range(RASTER_SIZE):
            if x < 4 or x >= 92 or y < 4 or y >= 92:
                pixels[y * RASTER_SIZE + x] = 0
    for pad, texture in ((scene.left_pad, scene.left_texture), (scene.right_pad, scene.right_texture)):
        for y in range(pad.y0, pad.y1):
            for x in range(pad.x0, pad.x1):
                cell = (x - pad.x0) // 8
                if texture == "checkerboard":
                    cell += (y - pad.y0) // 8
                pixels[y * RASTER_SIZE + x] = 255 if cell % 2 == 0 else 0
    for obstacle in scene.obstacles:
        for y in range(obstacle.y0, obstacle.y1):
            offset = y * RASTER_SIZE + obstacle.x0
            pixels[offset:offset + obstacle.x1 - obstacle.x0] = b"\xff" * (obstacle.x1 - obstacle.x0)
    return bytes(pixels)


def _validate_raster(raster: bytes) -> None:
    if type(raster) is not bytes or len(raster) != RASTER_SIZE * RASTER_SIZE:
        raise ValueError("raster must be exactly 9,216 bytes")


def _samples(raster: bytes, *, x_q: int, y_q: int) -> bytes:
    _validate_raster(raster)
    for coordinate in (x_q, y_q):
        if type(coordinate) is not int or not 4 * 256 <= coordinate <= 92 * 256:
            raise ValueError("observation position must be an integer in [1024, 23552]")
    # Integer floor division preserves negative-coordinate floor semantics.
    xs = [min(95, max(0, (x_q + (-60 + 8 * i) * 256) // 256)) for i in range(16)]
    ys = [min(95, max(0, (y_q + (-60 + 8 * i) * 256) // 256)) for i in range(16)]
    return bytes(raster[y * RASTER_SIZE + x] for y in ys for x in xs)


def observation(raster: bytes, *, x_q: int, y_q: int) -> Observation:
    """Sample the canonical raster; the controller receives only normalized pixels."""
    return Observation(schema_version="1", pixels=[pixel / 255 for pixel in _samples(raster, x_q=x_q, y_q=y_q)])


def raster_sha256(raster: bytes) -> str:
    _validate_raster(raster)
    return hashlib.sha256(raster).hexdigest()


def observation_sha256(raster: bytes, *, x_q: int, y_q: int) -> str:
    """SHA256 of 256 sampled raw bytes before normalization, in row-major order."""
    return hashlib.sha256(_samples(raster, x_q=x_q, y_q=y_q)).hexdigest()


def png_bytes(raster: bytes) -> bytes:
    """Losslessly encode the canonical raster for inspection/display; requires Pillow."""
    _validate_raster(raster)
    from PIL import Image

    output = BytesIO()
    Image.frombytes("L", (RASTER_SIZE, RASTER_SIZE), raster).save(output, format="PNG")
    return output.getvalue()
