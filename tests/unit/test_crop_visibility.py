"""Independent pixel checks for the v1 crop's destination visibility boundary."""
import pytest

from flytrap.arena.core import Q, Scene, State
from flytrap.arena.render import _samples, render
from scripts.feasibility_trace_diagnostics import sample_coordinates, visibility


@pytest.mark.parametrize("x_q", [4 * Q, 30 * Q + 13, 48 * Q, 60 * Q, 92 * Q])
@pytest.mark.parametrize("y_q", [88 * Q, 88 * Q + 1, 90 * Q, 92 * Q])
def test_v1_bottom_region_has_no_pad_rows_and_layouts_are_identical(x_q, y_q):
    left, right = Scene("stripes", "checkerboard"), Scene("checkerboard", "stripes")
    xs, ys = sample_coordinates(x_q, y_q)
    assert min(ys) >= 28
    assert not visibility(left, State(x_q, y_q))["any_pad_samples"]
    assert _samples(render(left), x_q=x_q, y_q=y_q) == _samples(render(right), x_q=x_q, y_q=y_q)
    assert len(xs) == len(ys) == 16


@pytest.mark.parametrize("position,expected_rows,different", [
    ((48, 76), [16, 24], True),
    ((60, 80), [20], True),
    ((30, 87), [27], True),
    ((48, 88), [], False),
    ((48, 92), [], False),
    ((4, 92), [], False),
])
def test_swapped_layouts_at_start_path_and_wall_have_position_specific_sensitivity(position, expected_rows, different):
    left, right = Scene("stripes", "checkerboard"), Scene("checkerboard", "stripes")
    x, y = position
    _, ys = sample_coordinates(x * Q, y * Q)
    assert [row for row in ys if 12 <= row < 28] == expected_rows
    first = _samples(render(left), x_q=x * Q, y_q=y * Q)
    second = _samples(render(right), x_q=x * Q, y_q=y * Q)
    assert (first != second) == different


def test_exact_start_sample_coordinates_and_pixels_match_independent_oracle():
    scene = Scene("stripes", "checkerboard")
    xs, ys = sample_coordinates(48 * Q, 76 * Q)
    assert xs == [0, 0, 4, 12, 20, 28, 36, 44, 52, 60, 68, 76, 84, 92, 95, 95]
    assert ys == [16, 24, 32, 40, 48, 56, 64, 72, 80, 88, 95, 95, 95, 95, 95, 95]
    pixels = _samples(render(scene), x_q=48 * Q, y_q=76 * Q)
    assert list(pixels[:16]) == [0, 0, 128, 255, 0, 255, 128, 128, 128, 255, 0, 255, 128, 0, 0, 0]
    assert list(pixels[16:32]) == [0, 0, 128, 255, 0, 255, 128, 128, 128, 0, 255, 0, 128, 0, 0, 0]
    assert pixels[160:] == bytes(96)
