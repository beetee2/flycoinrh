"""Exact full-raster downsampling, with no claims about neural competence."""

import pytest

from flytrap.arena.core import build_arena
from flytrap.arena.overview import overview_observation
from flytrap.arena.render import render
from scripts.feasibility import challenge_for


def test_overview_samples_exact_cell_centers_and_retains_layout_pixels():
    rasters = [render(build_arena(challenge_for(side)).scene) for side in ("left", "right")]
    observations = [overview_observation(raster) for raster in rasters]
    for raster, obs in zip(rasters, observations):
        assert obs.pixels == [raster[(3 + 6*y)*96 + 3 + 6*x]/255 for y in range(16) for x in range(16)]
        assert set(vars(obs)) == {"schema_version", "pixels"}
    assert observations[0] != observations[1]


@pytest.mark.parametrize("raster", [b"", bytes(9215), bytearray(9216)])
def test_overview_rejects_invalid_rasters(raster):
    with pytest.raises(ValueError):
        overview_observation(raster)
