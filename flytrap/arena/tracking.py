"""Development-only ``tracking16_v3`` partial-follow camera observation.

The virtual camera center is ``48 + (position - 48) / 4`` on each axis.
A 96-pixel field is sampled at 16 nearest cell centers, so movement changes
the image in four-world-pixel increments while both destination textures stay
in view throughout the allowed [4, 92] operating region. This fixed camera
rule is independent of scene content and scoring. It adds no avatar overlay.

Positions are environment-side inputs in 1/256-pixel units. Only the resulting
normalized pixels cross the controller boundary; camera coordinates do not.
"""

from flytrap.arena.render import RASTER_SIZE, _validate_raster
from flytrap.contracts import Observation


CROP_VERSION = "tracking16_v3"


def sample_coordinates(x_q: int, y_q: int) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Return exact clipped raster coordinates for the 16 by 16 sample grid."""
    for coordinate in (x_q, y_q):
        if type(coordinate) is not int or not 4 * 256 <= coordinate <= 92 * 256:
            raise ValueError("observation position must be an integer in [1024, 23552]")

    def axis(coordinate: int) -> tuple[int, ...]:
        return tuple(min(95, max(0, (4 * (3 + 6 * i) * 256 + coordinate - 48 * 256) // 1024))
                     for i in range(16))

    return axis(x_q), axis(y_q)


def samples(raster: bytes, *, x_q: int, y_q: int) -> bytes:
    """Return the 256 sampled grayscale bytes in row-major order."""
    _validate_raster(raster)
    xs, ys = sample_coordinates(x_q, y_q)
    return bytes(raster[y * RASTER_SIZE + x] for y in ys for x in xs)


def tracking_observation(raster: bytes, *, x_q: int, y_q: int) -> Observation:
    """Sample the canonical raster into the existing pixels-only envelope."""
    return Observation(schema_version="1", pixels=[
        pixel / 255 for pixel in samples(raster, x_q=x_q, y_q=y_q)
    ])
