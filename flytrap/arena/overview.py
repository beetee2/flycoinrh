"""Development-only overview16_v2: fixed full-scene nearest center sampling.

This task-independent downsample uses the same 16x16 pixel-only envelope.
No avatar, position, pad labels, scoring, or other metadata is added.
The v1 renderer and egocentric crop remain unchanged.
"""

from flytrap.arena.render import _validate_raster
from flytrap.contracts import Observation

CROP_VERSION = "overview16_v2"
SAMPLE_COORDINATES = tuple(3 + 6 * index for index in range(16))


def overview_observation(raster: bytes) -> Observation:
    _validate_raster(raster)
    return Observation(schema_version="1", pixels=[
        raster[y * 96 + x] / 255 for y in SAMPLE_COORDINATES for x in SAMPLE_COORDINATES
    ])
