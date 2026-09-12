"""Synthetic renderer fixtures validate pixels, never model competence."""

from dataclasses import replace
import hashlib
from io import BytesIO
import json
from pathlib import Path

from hypothesis import given, strategies as st
from PIL import Image
import pytest

from flytrap.arena.core import Rect, Scene
from flytrap.arena.render import observation, observation_sha256, png_bytes, raster_sha256, render


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "arena"
GOLDEN = json.loads((FIXTURES / "golden.json").read_text())


def golden_scene():
    return Scene(left_texture="stripes", right_texture="checkerboard", obstacles=(
        Rect(44, 36, 52, 40), Rect(44, 48, 52, 52), Rect(44, 60, 52, 64),
    ))


def test_raster_matches_independent_hand_assembled_golden():
    pixels = render(golden_scene())
    assert type(pixels) is bytes
    assert len(pixels) == 96 * 96
    assert pixels == (FIXTURES / "stripes_left_all_obstacles.gray").read_bytes()
    assert raster_sha256(pixels) == GOLDEN["raster_sha256"]
    assert GOLDEN["fixture"] is True


@pytest.mark.parametrize("name", list(GOLDEN["observations"]))
def test_crop_matches_independently_calculated_sample_hashes(name):
    golden = GOLDEN["observations"][name]
    x_q, y_q = golden["position_q"]
    pixels = render(golden_scene())
    result = observation(pixels, x_q=x_q, y_q=y_q)
    assert result.schema_version == "1"
    assert len(result.pixels) == 256
    assert set(result.pixels) <= {0.0, 128 / 255, 1.0}
    assert set(result.model_dump()) == {"schema_version", "pixels"}
    assert observation_sha256(pixels, x_q=x_q, y_q=y_q) == golden["sha256"]
    assert hashlib.sha256(bytes(round(p * 255) for p in result.pixels)).hexdigest() == golden["sha256"]


def test_half_open_pad_texture_and_obstacle_edges():
    pixels = render(golden_scene())

    def at(x, y):
        return pixels[y * 96 + x]
    assert [at(x, 12) for x in (11, 12, 19, 20, 27, 28, 35, 36)] == [128, 255, 255, 0, 0, 255, 255, 128]
    assert [at(12, y) for y in (11, 12, 19, 20, 27, 28)] == [128, 255, 255, 255, 255, 128]
    assert [at(60, y) for y in (11, 12, 19, 20, 27, 28)] == [128, 255, 255, 0, 0, 128]
    assert [at(x, 36) for x in (43, 44, 51, 52)] == [128, 255, 255, 128]
    assert [at(44, y) for y in (35, 36, 39, 40)] == [128, 255, 255, 128]


def test_swapping_textures_changes_only_pad_pattern_pixels():
    scene = golden_scene()
    original = render(scene)
    swapped = render(replace(scene, left_texture="checkerboard", right_texture="stripes"))
    changed = {i for i, (old, new) in enumerate(zip(original, swapped)) if old != new}
    assert changed == {y * 96 + x for y in range(20, 28) for x in (*range(12, 36), *range(60, 84))}


def test_fractional_samples_floor_at_pixel_boundary():
    # A labeled ramp exposes crop ordering and subpixel rounding independent of
    # the arena's flat background and eight-pixel pattern cells.
    ramp = bytes((x + 3 * y) % 256 for y in range(96) for x in range(96))
    just_before = observation(ramp, x_q=48 * 256 - 1, y_q=48 * 256 - 1).pixels
    at_boundary = observation(ramp, x_q=48 * 256, y_q=48 * 256).pixels
    assert just_before[2 * 16 + 2] == 12 / 255  # world (3, 3)
    assert at_boundary[2 * 16 + 2] == 16 / 255  # world (4, 4)
    assert at_boundary[2 * 16 + 3] == 24 / 255  # world (12, 4)
    assert at_boundary[3 * 16 + 2] == 40 / 255  # world (4, 12)
    assert at_boundary[0] == 0.0
    assert at_boundary[-1] == 124 / 255  # clipped world (95, 95)


@given(x_q=st.integers(1024, 23552), y_q=st.integers(1024, 23552))
def test_crop_samples_stay_in_raster_and_normalization_roundtrips(x_q, y_q):
    raster = bytes(range(256)) * 36
    pixels = observation(raster, x_q=x_q, y_q=y_q).pixels
    assert len(pixels) == 256
    assert all(0 <= p <= 1 for p in pixels)
    raw = bytes(round(p * 255) for p in pixels)
    assert observation_sha256(raster, x_q=x_q, y_q=y_q) == hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize("coordinate", [True, False, 4.0, "1024", None, float("nan"),
                                         float("inf"), -float("inf"), 1023, 23553])
@pytest.mark.parametrize("axis", ["x_q", "y_q"])
def test_observation_rejects_nonfinite_and_malformed_positions(coordinate, axis):
    position = {"x_q": 12288, "y_q": 20480, axis: coordinate}
    raster = bytes(96 * 96)
    for sample in (observation, observation_sha256):
        with pytest.raises(ValueError, match="position"):
            sample(raster, **position)


@pytest.mark.parametrize("raster", [b"", bytes(9215), bytes(9217), bytearray(9216),
                                     memoryview(bytes(9216)), [0] * 9216, None, "0" * 9216])
def test_raster_helpers_reject_malformed_or_mutable_buffers(raster):
    for helper in (raster_sha256, png_bytes):
        with pytest.raises(ValueError, match="raster"):
            helper(raster)
    for helper in (observation, observation_sha256):
        with pytest.raises(ValueError, match="raster"):
            helper(raster, x_q=12288, y_q=20480)


def test_renderer_revalidates_bypassed_scene():
    scene = golden_scene()
    object.__setattr__(scene, "width", float("nan"))
    with pytest.raises(ValueError):
        render(scene)
    with pytest.raises(ValueError, match="Scene"):
        render({"width": 96})


def test_png_decodes_to_exact_same_sensory_raster():
    raster = render(golden_scene())
    encoded = png_bytes(raster)
    with Image.open(BytesIO(encoded)) as image:
        assert image.mode == "L"
        assert image.size == (96, 96)
        assert image.tobytes() == raster


def test_renderer_cannot_accept_hidden_metadata_or_overlay():
    with pytest.raises(TypeError):
        render(golden_scene(), destination_side="right")
    with pytest.raises(TypeError):
        observation(bytes(9216), x_q=12288, y_q=20480, score=1)
