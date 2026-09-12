"""Synthetic metric oracles; no neural execution or task-competence evidence."""
from copy import deepcopy

import pytest

from flytrap.arena.core import Q, Scene, State
from flytrap.arena.render import render
from scripts.feasibility_revision import observe
from scripts.feasibility_revision_analysis import compare, image_sheet, rates_summary, visibility_for


def row(tick, *, x=48, y=76, dx=0.0, dy=0.0, click=False, digest="a", rates=None):
    return dict(before=dict(tick=tick - 1, x_q=48 * Q, y_q=76 * Q, outcome=None),
                after=dict(tick=tick, x_q=x * Q, y_q=y * Q, outcome=None),
                action=dict(dx=dx, dy=dy, click=click), observation_sha256=digest * 64,
                motor_rates=rates or dict(steer_L=0, steer_R=0, fwd_L=0, fwd_R=0, back=0, stop=0))


def test_compare_separates_pixels_actions_positions_and_final_distance():
    first = [row(1), row(2), row(3)]
    second = [row(1, digest="b"), row(2, dx=0.5), row(3, x=51, y=80)]
    assert compare(first, second) == dict(matched_ticks=3, a_ticks=3, b_ticks=3, last_common_tick=3, different_inputs=1,
        different_motor_actions=1, different_positions=1, separation_at_last_common_tick_pixels=5.0,
        endpoint_separation_pixels=5.0)


def test_compare_identical_motor_and_pixels_can_have_different_physics_positions():
    first = [row(1, x=4, y=76, dx=-1, dy=-1)]
    second = [row(1, x=4, y=68, dx=-1, dy=-1)]
    result = compare(first, second)
    assert result["different_inputs"] == result["different_motor_actions"] == 0
    assert result["different_positions"] == 1
    assert result["separation_at_last_common_tick_pixels"] == 8


def test_compare_unchanged_final_position_does_not_hide_path_differences():
    first = [row(1), row(2)]
    second = [row(1, x=52), row(2)]
    result = compare(first, second)
    assert result["different_positions"] == 1
    assert result["separation_at_last_common_tick_pixels"] == 0


def test_compare_includes_recorded_click_in_action_differences():
    first = [row(1)]
    second = deepcopy(first)
    second[0]["action"]["click"] = True
    assert compare(first, second)["different_motor_actions"] == 1


def test_rates_summary_uses_recorded_signed_actions_and_strict_mdn_threshold():
    # Stop can cancel speed even with greater MDN than mean forward rate.
    rows = [row(1, dy=0, rates=dict(steer_L=10, steer_R=30, fwd_L=100, fwd_R=300, back=300, stop=450)),
            row(2, dy=-0.1, rates=dict(steer_L=30, steer_R=10, fwd_L=200, fwd_R=200, back=200, stop=449)),
            row(3, dy=0.1, rates=dict(steer_L=20, steer_R=20, fwd_L=0, fwd_R=0, back=300, stop=451))]
    result = rates_summary(rows)
    assert result["ticks"] == 3
    assert result["rates_hz"]["steer_L"] == dict(mean=20, minimum=10, maximum=30)
    assert result["rates_hz"]["stop"] == dict(mean=450, minimum=449, maximum=451)
    assert result["mdn_exceeds_mean_dna01_ticks"] == 2
    assert result["stop_at_least_450_hz_ticks"] == 2
    assert result["upward_requested_ticks"] == result["downward_requested_ticks"] == 1


def test_empty_contact_group_does_not_invent_zero_rates():
    assert rates_summary([]) == dict(ticks=0)


@pytest.mark.parametrize("crop,position,counts", [
    ("crop16_v1", (48, 76), {"left": 6, "right": 6}),
    ("crop16_v1", (48, 88), {"left": 0, "right": 0}),
    ("overview16_v2", (48, 76), {"left": 12, "right": 12}),
    ("overview16_v2", (4, 92), {"left": 12, "right": 12}),
])
def test_visibility_counts_geometric_sample_locations_independently_of_black_input(crop, position, counts):
    scene = Scene("stripes", "checkerboard")
    state = State(position[0] * Q, position[1] * Q)
    geometric = visibility_for(crop)(scene, state)
    assert geometric["pad_samples"] == counts
    assert geometric["any_pad_samples"] == any(counts.values())
    assert observe(render(scene), state, crop, "dark").pixels == [0.0] * 256


def test_compare_early_terminal_reports_common_tick_and_separate_endpoints():
    first = [row(1, x=48), row(2, x=51)]
    second = [row(1, x=52)]
    second[0]["after"]["outcome"] = "success"
    result = compare(first, second)
    assert (result["a_ticks"], result["b_ticks"], result["matched_ticks"], result["last_common_tick"]) == (2, 1, 1, 1)
    assert result["separation_at_last_common_tick_pixels"] == 4
    assert result["endpoint_separation_pixels"] == 1


@pytest.mark.parametrize("first,second", [([], [row(1)]), ([row(1)], []),
    ([row(2)], [row(1)]), ([row(1), row(3)], [row(1), row(2)]),
    ([{**row(1), "after": {**row(1)["after"], "tick": 2}}], [row(1)])])
def test_compare_rejects_missing_empty_or_misaligned_ticks(first, second):
    with pytest.raises(ValueError):
        compare(first, second)


@pytest.mark.parametrize("outcome,expected", [("success", "TERMINAL: success"),
    ("wrong_pad", "TERMINAL: wrong_pad"), (None, "INCOMPLETE cutoff")])
def test_image_sheet_uses_actual_short_trace_and_saved_input_without_tick_95(tmp_path, monkeypatch, outcome, expected):
    from PIL import Image, ImageDraw

    trial_dir = tmp_path / "trial"
    trial_dir.mkdir()
    Image.new("RGB", (576, 666), "gray").save(trial_dir / "trajectory.png")
    Image.new("L", (16, 16), 77).save(trial_dir / "input-000.png")
    labels = []
    original = ImageDraw.ImageDraw.text

    def capture(self, xy, text, *args, **kwargs):
        labels.append(text)
        return original(self, xy, text, *args, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", capture)
    image_sheet([dict(input="canonical", directory=str(trial_dir), ticks=1,
        physics="tangent_v2", crop="crop16_v1", seed=7, layout="left", outcome=outcome,
        diagnosis=dict(stationary_causes=dict(zero_motor=0, quantization=0, collision=0),
                       controller_pad_visible_observation_count=1))], tmp_path, "canonical")
    assert (tmp_path / "canonical-trajectories-inputs.png").is_file()
    assert f"{expected}; stationary 0/1" in labels
    assert "Pad-visible inputs 1/1" in labels
    assert "input 0" in labels
    assert not any("95" in label or "96 ticks" in label for label in labels)
