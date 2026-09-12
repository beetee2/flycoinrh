"""Exact candidate pixels and whole-region visibility; no competence claims."""

from fractions import Fraction
import math

from hypothesis import given, settings, strategies as st
import pytest

from flytrap.arena.core import Q, Scene
from flytrap.arena.overview import overview_observation
from flytrap.arena.render import render
from flytrap.arena.tracking import CROP_VERSION, sample_coordinates, samples, tracking_observation


MIN_Q = 4 * Q
MAX_Q = 92 * Q
# Each starts a distinct camera quantization bin; the last bin is the upper
# operating endpoint. Bins include every legal 1/256-world-pixel position.
BIN_STARTS = tuple(range(MIN_Q, MAX_Q + 1, 4 * Q))


def scalar_axis(position_q):
    """Independent rational camera/FOV oracle, without production arithmetic."""
    center = 48 + (Fraction(position_q, Q) - 48) / 4
    return tuple(max(0, min(95, math.floor(center - 48 + Fraction(2 * i + 1, 2) * 6)))
                 for i in range(16))


def scalar_pixels(raster, x_q, y_q):
    return bytes(raster[y * 96 + x] for y in scalar_axis(y_q) for x in scalar_axis(x_q))


def test_tracking_version_and_hand_calculated_start_coordinates():
    assert CROP_VERSION == "tracking16_v3"
    xs, ys = sample_coordinates(48 * Q, 76 * Q)
    assert xs == (3, 9, 15, 21, 27, 33, 39, 45, 51, 57, 63, 69, 75, 81, 87, 93)
    assert ys == (10, 16, 22, 28, 34, 40, 46, 52, 58, 64, 70, 76, 82, 88, 94, 95)
    raster = render(Scene("stripes", "checkerboard"))
    raw = samples(raster, x_q=48 * Q, y_q=76 * Q)
    assert tuple(raw[16:32]) == (0, 128, 255, 0, 0, 255, 128, 128, 128, 128, 255, 0, 0, 255, 128, 0)
    assert tuple(raw[32:48]) == (0, 128, 255, 0, 0, 255, 128, 128, 128, 128, 0, 255, 255, 0, 128, 0)


@pytest.mark.property
@settings(max_examples=50)
@given(tile=st.binary(min_size=256, max_size=256),
       x_q=st.integers(MIN_Q, MAX_Q), y_q=st.integers(MIN_Q, MAX_Q))
def test_exact_sample_bytes_and_normalization_match_independent_scalar_oracle(tile, x_q, y_q):
    raster = tile * 36
    expected = scalar_pixels(raster, x_q, y_q)
    assert sample_coordinates(x_q, y_q) == (scalar_axis(x_q), scalar_axis(y_q))
    assert samples(raster, x_q=x_q, y_q=y_q) == expected
    observation = tracking_observation(raster, x_q=x_q, y_q=y_q)
    assert observation.pixels == [value / 255 for value in expected]
    assert bytes(round(value * 255) for value in observation.pixels) == expected
    assert set(observation.model_dump()) == {"schema_version", "pixels"}


def test_23_axis_bins_cover_every_legal_quantized_world_position():
    assert len(BIN_STARTS) == 23
    grids = tuple(scalar_axis(start) for start in BIN_STARTS)
    assert len(set(grids)) == 23
    for position_q in range(MIN_Q, MAX_Q + 1):
        index = (position_q - MIN_Q) // (4 * Q)
        xs, ys = sample_coordinates(position_q, position_q)
        assert xs == ys == grids[index]


@pytest.mark.parametrize("x_q", BIN_STARTS, ids=lambda q: f"x{q // Q}")
@pytest.mark.parametrize("y_q", BIN_STARTS, ids=lambda q: f"y{q // Q}")
def test_both_pads_retain_bright_dark_contrast_and_layout_difference_in_every_camera_bin(x_q, y_q):
    """529 bin pairs exhaust the entire allowed square, including both walls."""
    scenes = (Scene("stripes", "checkerboard"), Scene("checkerboard", "stripes"))
    xs, ys = scalar_axis(x_q), scalar_axis(y_q)
    observations = []
    for scene in scenes:
        raster = render(scene)
        raw = samples(raster, x_q=x_q, y_q=y_q)
        assert raw == scalar_pixels(raster, x_q, y_q)
        observations.append(raw)
        for pad in (scene.left_pad, scene.right_pad):
            visible = [raw[j * 16 + i] for j, y in enumerate(ys) for i, x in enumerate(xs)
                       if pad.x0 <= x < pad.x1 and pad.y0 <= y < pad.y1]
            assert visible
            assert set(visible) == {0, 255}
    assert observations[0] != observations[1]


@pytest.mark.parametrize("position", [(4, 4), (92, 4), (4, 92), (92, 92), (48, 48), (48, 76)])
def test_movement_changes_actual_scene_pixels_at_representative_positions(position):
    raster = render(Scene("stripes", "checkerboard"))
    current = samples(raster, x_q=position[0] * Q, y_q=position[1] * Q)
    center = samples(raster, x_q=48 * Q, y_q=76 * Q)
    assert current == scalar_pixels(raster, position[0] * Q, position[1] * Q)
    assert (current != center) == (position != (48, 76))


def test_overview_has_no_movement_feedback_but_tracking_does():
    raster = render(Scene("stripes", "checkerboard"))
    positions = ((48, 76), (4, 92), (92, 92), (4, 4), (92, 4), (48, 48))
    overview = [tuple(overview_observation(raster).pixels) for _ in positions]
    tracking = [samples(raster, x_q=x * Q, y_q=y * Q) for x, y in positions]
    assert len(set(overview)) == 1
    assert len(set(tracking)) == len(positions)
    # Movement below a camera quantization step is deliberately not visible.
    assert samples(raster, x_q=48 * Q, y_q=76 * Q) == samples(raster, x_q=52 * Q - 1, y_q=80 * Q - 1)
    assert samples(raster, x_q=48 * Q, y_q=76 * Q) != samples(raster, x_q=52 * Q, y_q=80 * Q)


@pytest.mark.parametrize("coordinate", [True, False, 1024.0, "1024", None, float("nan"),
                                         float("inf"), -float("inf"), 1023, 23553])
@pytest.mark.parametrize("axis", ["x_q", "y_q"])
def test_rejects_same_malformed_and_out_of_region_positions_as_v1(coordinate, axis):
    position = {"x_q": 48 * Q, "y_q": 76 * Q, axis: coordinate}
    with pytest.raises(ValueError, match="position"):
        sample_coordinates(**position)
    for helper in (samples, tracking_observation):
        with pytest.raises(ValueError, match="position"):
            helper(bytes(9216), **position)


@pytest.mark.parametrize("raster", [b"", bytes(9215), bytes(9217), bytearray(9216),
                                     memoryview(bytes(9216)), [0] * 9216, None, "0" * 9216])
def test_rejects_noncanonical_raster_buffers(raster):
    for helper in (samples, tracking_observation):
        with pytest.raises(ValueError, match="raster"):
            helper(raster, x_q=48 * Q, y_q=76 * Q)


def test_camera_accepts_no_scene_or_hidden_metadata():
    with pytest.raises(ValueError, match="raster"):
        tracking_observation(Scene("stripes", "checkerboard"), x_q=48 * Q, y_q=76 * Q)
    for forbidden in ("goal", "destination_side", "score", "state", "arena", "avatar"):
        with pytest.raises(TypeError):
            tracking_observation(bytes(9216), x_q=48 * Q, y_q=76 * Q, **{forbidden: "hidden"})
