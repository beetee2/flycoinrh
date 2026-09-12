"""Synthetic fixture traces for final diagnostics; no neural model is invoked."""

from copy import deepcopy
from dataclasses import asdict
import hashlib
import json

import pytest

from flytrap.arena.core import MAX_TICKS, Q, State, build_arena, initial_state
from flytrap.arena.render import render
from flytrap.arena.sliding import step_sliding
from flytrap.contracts import ControllerOutput
from scripts.feasibility import challenge_for
from scripts.feasibility_final import observe
from scripts.feasibility_final_analysis import compare, derive_black, metrics
from scripts.feasibility_final_motor import calibrate


RATES = dict(steer_L=100, steer_R=80, fwd_L=50, fwd_R=70, back=100, stop=20)
ZERO_RATES = dict.fromkeys(RATES, 0)


def fixture_action(dx=0.0, dy=0.0):
    return ControllerOutput(schema_version="1", dx=dx, dy=dy, click=False, model_mode="fixture",
                            telemetry=dict(schema_version="1", sampled_neurons=2, spike_count=3, neural_ms=20))


def fixture_trial(*, layout="left", kind="canonical", crop="tracking16_v3", motor="upstream_pilot_v1"):
    return dict(id="SYNTHETIC-TEST-ONLY", fixture=True, stage="screen", seed=7, layout=layout,
                input=kind, crop=crop, motor=motor, physics="tangent_v2", tick_limit=MAX_TICKS)


def fixture_rows(actions, *, trial=None, start=None, raw_actions=None, rates=None):
    """Advance real deterministic physics using explicit synthetic actions only."""
    trial = trial or fixture_trial()
    arena = build_arena(challenge_for(trial["layout"]))
    raster = render(arena.scene)
    state, rows = start or initial_state(), []
    raw_actions = raw_actions or actions
    for index, (action, raw) in enumerate(zip(actions, raw_actions)):
        pixels = bytes(round(value*255) for value in observe(raster, state, trial["crop"], trial["input"]).pixels)
        after = step_sliding(arena, state, action)
        rows.append(dict(before=asdict(state), after=asdict(after), raw_action=raw.model_dump(),
                         action=action.model_dump(), motor_rates=dict(RATES if rates is None else rates),
                         observation_pixels=list(pixels), observation_sha256=hashlib.sha256(pixels).hexdigest(),
                         step_wall_seconds=(index+1)/10))
        state = after
        if state.outcome is not None:
            break
    return rows


def fixture_black_source(tmp_path, *, length=3, motor="dark_balance_v3", rates=None):
    trial = fixture_trial(kind="dark", motor=motor)
    raw = fixture_action(-0.25, 0.5) if rates is None else fixture_action()
    motor_rates = RATES if rates is None else rates
    action = calibrate(raw, motor_rates, motor)
    rows = fixture_rows([action]*length, trial=trial, raw_actions=[raw]*length, rates=motor_rates)
    payload = "".join(json.dumps(row)+"\n" for row in rows).encode()
    source_path = tmp_path / "synthetic-source.jsonl"
    source_path.write_bytes(payload)
    trial.update(trace_sha256=hashlib.sha256(payload).hexdigest(), ticks=len(rows),
                 final_state=rows[-1]["after"], outcome=rows[-1]["after"]["outcome"],
                 termination="terminal" if rows[-1]["after"]["outcome"] else "diagnostic_cutoff")
    return trial, rows


def test_motion_oracle_separates_raw_requested_quantized_and_executed_corner_movement():
    actions = [fixture_action(-0.25, 0.5), fixture_action(-0.25, 0.5),
               fixture_action(0.0001, -0.0001), fixture_action()]
    raw = [fixture_action(-0.5, 0.75), fixture_action(-0.5, 0.75),
           fixture_action(0.001, -0.001), fixture_action()]
    rows = fixture_rows(actions, raw_actions=raw, start=State(5*Q, 91*Q))
    result = metrics(rows, fixture_trial())
    assert result["motion_pixels"]["raw_requested"] == pytest.approx([-7.992, 11.992])
    assert result["motion_pixels"]["requested"] == pytest.approx([-3.9992, 7.9992])
    assert result["motion_pixels"]["quantized"] == [-4, 8]
    assert result["motion_pixels"]["executed"] == [-1, 1]
    assert result["mean_requested_pixels"] == pytest.approx([-0.9998, 1.9998])
    assert result["directions"] == dict(left=2, right=1, up=1, down=2)
    assert result["stationary_causes"] == dict(zero_motor=1, quantization=1, collision=1)
    assert result["wall_corner_before_ticks"] == dict(left=3, right=0, top=0, bottom=3,
                                                      left_top=0, left_bottom=3, right_top=0, right_bottom=0)
    assert result["exact_wall_before_ticks"] == 3
    assert result["outward_at_wall_ticks"] == 1
    assert result["first_wall_contact_tick"] == 1
    assert result["boundary_band_before_ticks"] == 4
    assert result["boundary_band_fraction"] == 1
    assert result["x_extent_pixels"] == [4, 5]
    assert result["y_extent_pixels"] == [91, 92]
    assert result["mean_rates_hz"] == RATES
    assert result["summary"]["controller_wall_seconds"] == 1.0


@pytest.mark.parametrize("position,expected", [
    ((12*Q, 48*Q), 1), ((12*Q+1, 48*Q), 0), ((84*Q, 48*Q), 1), ((84*Q-1, 48*Q), 0),
    ((48*Q, 12*Q), 1), ((48*Q, 12*Q+1), 0), ((48*Q, 84*Q), 1), ((48*Q, 84*Q-1), 0),
])
def test_boundary_band_includes_exactly_eight_pixels_from_any_wall(position, expected):
    rows = fixture_rows([fixture_action()], start=State(*position))
    result = metrics(rows, fixture_trial())
    assert result["boundary_band_before_ticks"] == expected
    assert result["exact_wall_before_ticks"] == 0


@pytest.mark.parametrize("kind,visible,changed", [("canonical", 3, 1), ("dark", 0, 0)])
def test_feedback_counts_movement_within_camera_bin_separately_from_crossing_bin(kind, visible, changed):
    trial = fixture_trial(kind=kind)
    rows = fixture_rows([fixture_action(0.125, 0), fixture_action(0.375, 0), fixture_action()], trial=trial)
    result = metrics(rows, trial)
    assert rows[0]["observation_sha256"] == rows[1]["observation_sha256"]
    assert (rows[1]["observation_sha256"] != rows[2]["observation_sha256"]) == (kind == "canonical")
    assert result["any_pad_visible_inputs"] == visible
    assert result["both_pads_visible_inputs"] == visible
    assert result["both_pads_contrast_inputs"] == visible
    assert result["moved_steps_with_next_input"] == 2
    assert result["movement_followed_by_changed_input"] == changed
    assert result["adjacent_input_changes"] == changed


@pytest.mark.parametrize("crop,kind,visible", [
    ("crop16_v1", "canonical", 0), ("tracking16_v3", "canonical", 1), ("tracking16_v3", "dark", 0),
])
def test_bottom_wall_visibility_reports_supplied_pixels_and_camera_version(crop, kind, visible):
    trial = fixture_trial(crop=crop, kind=kind)
    result = metrics(fixture_rows([fixture_action()], trial=trial, start=State(48*Q, 92*Q)), trial)
    assert result["any_pad_visible_inputs"] == result["both_pads_visible_inputs"] == visible
    assert result["both_pads_contrast_inputs"] == visible


def test_exploration_includes_initial_and_all_executed_positions_in_eight_pixel_bins():
    rows = fixture_rows([fixture_action(1, 0), fixture_action(0, 1), fixture_action(-1, 0)])
    result = metrics(rows, fixture_trial())
    assert result["visited_8px_bins"] == 4
    assert result["visited_bin_coordinates"] == [(6, 9), (6, 10), (7, 9), (7, 10)]
    assert result["x_extent_pixels"] == [48, 56]
    assert result["y_extent_pixels"] == [76, 84]
    assert result["boundary_band_before_ticks"] == 1
    assert result["first_wall_contact_tick"] is None


@pytest.mark.parametrize("length,expected", [(3, None), (MAX_TICKS, "trial_timeout")])
def test_partial_diagnostic_still_has_no_outcome_and_only_full_episode_can_timeout(length, expected):
    result = metrics(fixture_rows([fixture_action()]*length), fixture_trial())
    assert result["summary"]["steps"] == length
    assert result["summary"]["outcome"] == expected
    assert result["pad_contacts"] == 0
    assert result["visited_8px_bins"] == 1
    assert result["stationary_causes"] == dict(zero_motor=length, quantization=0, collision=0)


@pytest.mark.parametrize("layout,outcome", [("left", "success"), ("right", "wrong_pad")])
def test_contact_is_counted_under_both_hidden_scoring_rules_without_learning_claim(layout, outcome):
    trial = fixture_trial(layout=layout)
    actions = [fixture_action(-1, 0)]*3 + [fixture_action(0, -1)]*8
    rows = fixture_rows(actions, trial=trial)
    result = metrics(rows, trial)
    assert len(rows) == 9
    assert result["summary"]["outcome"] == outcome
    assert result["pad_contacts"] == 1
    assert not any("recognition" in key or "learning" in key for key in result)


@pytest.mark.parametrize("corruption", ["condition", "pixel"])
def test_derived_black_rejects_nonblack_sources_before_publishing(tmp_path, corruption):
    source, rows = fixture_black_source(tmp_path)
    if corruption == "condition":
        source["input"] = "canonical"
    else:
        rows[1]["observation_pixels"][17] = 1
    output = tmp_path / "derived"
    output.mkdir()
    with pytest.raises(ValueError, match="all-black"):
        derive_black(source, rows, output, "right", "dark_balance_v3")
    assert list(output.iterdir()) == []


@pytest.mark.parametrize("side", ["left", "right"])
@pytest.mark.parametrize("motor", ["upstream_pilot_v1", "dark_balance_v3"])
def test_derived_black_reuses_exact_rate_sequence_and_recomputes_mapping_physics(tmp_path, side, motor):
    source, rows = fixture_black_source(tmp_path)
    pristine = deepcopy((source, rows))
    output = tmp_path / "derived"
    output.mkdir()
    trial, derived = derive_black(source, rows, output, side, motor)
    expected_actions = [calibrate(ControllerOutput.model_validate(row["raw_action"]), row["motor_rates"], motor)
                        for row in rows]
    expected = fixture_rows(expected_actions, trial=fixture_trial(layout=side, kind="dark", motor=motor),
                            raw_actions=[ControllerOutput.model_validate(row["raw_action"]) for row in rows])
    assert (source, rows) == pristine
    assert trial["fixture"] is True
    assert trial["derived"] is True
    assert trial["source_trial"] == source["id"]
    assert trial["source_trace_sha256"] == source["trace_sha256"]
    assert trial["additional_model_calls"] == 0
    assert trial["termination"] == "source_prefix_cutoff"
    assert trial["outcome"] is None
    assert trial["elapsed_wall_seconds"] == 0
    assert trial["ticks"] == len(rows) == 3
    for index, (old, new, oracle) in enumerate(zip(rows, derived, expected)):
        assert new["source_window"] == index
        assert new["reused_model_step_wall_seconds"] == old["step_wall_seconds"]
        assert new["step_wall_seconds"] == 0
        for field in ("raw_action", "motor_rates", "observation_pixels", "observation_sha256"):
            assert new[field] == old[field]
        for field in ("before", "after", "action"):
            assert new[field] == oracle[field]
        if motor == "dark_balance_v3":
            assert new["before"] == old["before"]
            assert new["after"] == old["after"]
        else:
            assert new["action"] == old["raw_action"]
            assert new["after"] != old["after"]
    path = output / trial["id"]
    payload = (path / "trace.jsonl").read_bytes()
    assert hashlib.sha256(payload).hexdigest() == trial["trace_sha256"]
    assert [json.loads(line) for line in payload.splitlines()] == derived
    assert json.loads((path / "trial.json").read_text())["source_trial"] == source["id"]
    assert metrics(derived, trial)["summary"]["controller_wall_seconds"] == 0


def test_exact_black_reuse_can_score_timeout_only_when_all_256_source_windows_exist(tmp_path):
    source, rows = fixture_black_source(tmp_path, length=MAX_TICKS, rates=ZERO_RATES)
    trial, derived = derive_black(source, rows, tmp_path, "right", "upstream_pilot_v1")
    assert len(derived) == trial["ticks"] == MAX_TICKS
    assert trial["termination"] == "terminal"
    assert trial["outcome"] == "trial_timeout"
    assert trial["additional_model_calls"] == 0
    assert metrics(derived, trial)["pad_contacts"] == 0


def test_derived_trial_does_not_publish_inherited_source_metrics(tmp_path):
    source, rows = fixture_black_source(tmp_path)
    source["metrics"] = {"source_only_sentinel": "these describe a different trajectory"}
    trial, derived = derive_black(source, rows, tmp_path, "right", "upstream_pilot_v1")
    saved = json.loads((tmp_path / trial["id"] / "trial.json").read_text())
    assert "metrics" not in saved
    assert "source_only_sentinel" in source["metrics"]
    assert metrics(derived, trial) != source["metrics"]


def test_comparison_keeps_partial_lengths_and_common_tick_separation_distinct_from_endpoints():
    first = fixture_rows([fixture_action(0.5, 0), fixture_action(0.5, 0)])
    second = fixture_rows([fixture_action(0, 0.5)])
    result = compare(first, second)
    assert result["a_ticks"] == 2
    assert result["b_ticks"] == result["matched_ticks"] == result["last_common_tick"] == 1
    assert result["different_inputs"] == 0
    assert result["different_motor_actions"] == result["different_positions"] == 1
    assert result["separation_at_last_common_tick_pixels"] == pytest.approx(32**0.5)
    assert result["endpoint_separation_pixels"] == pytest.approx(80**0.5)


def test_comparison_reports_distinct_layout_pixels_without_inventing_action_changes():
    first = fixture_rows([fixture_action()], trial=fixture_trial(layout="left"))
    second = fixture_rows([fixture_action()], trial=fixture_trial(layout="right"))
    result = compare(first, second)
    assert result["different_inputs"] == 1
    assert result["different_motor_actions"] == result["different_positions"] == 0


@pytest.mark.parametrize("corruption", ["empty", "missing_first", "gap"])
def test_comparison_rejects_empty_and_misaligned_prefixes(corruption):
    first = fixture_rows([fixture_action()]*3)
    second = deepcopy(first)
    if corruption == "empty":
        second.clear()
    elif corruption == "missing_first":
        second.pop(0)
    else:
        second.pop(1)
    with pytest.raises(ValueError):
        compare(first, second)
