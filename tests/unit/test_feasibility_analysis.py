"""Synthetic development records validate metrics, never real-model feasibility."""

from copy import deepcopy
from dataclasses import asdict

import pytest

from flytrap.arena.core import MAX_TICKS, Q, State
from scripts.feasibility_analysis import latency_distribution, summarize_trace, summarize_visual_pairs


def action(dx=0.0, dy=0.0):
    return dict(schema_version="1", dx=dx, dy=dy, click=False, model_mode="fixture",
                telemetry=dict(schema_version="1", sampled_neurons=2, spike_count=3, neural_ms=20.0))


def trace():
    positions = [(48, 76), (51, 80), (51, 80), (51, 80), (51, 79), (51, 79)]
    return [dict(before=asdict(State(x * Q, y * Q, tick=i)),
                 after=asdict(State(nx * Q, ny * Q, tick=i + 1)),
                 action=action(0.375, 0.5) if i == 0 else action(0.0, -0.125),
                 step_wall_seconds=seconds, observation_sha256=str(i % 2) * 64)
            for i, (((x, y), (nx, ny)), seconds) in enumerate(
                zip(zip(positions, positions[1:]), (0.1, 0.4, 0.3, 0.2, 0.5)))]


def test_trace_measures_stuck_physics_independently_of_nonzero_motor():
    result = summarize_trace(trace())
    assert result == dict(
        steps=5, environment_ticks=5, outcome=None,
        step_latency_seconds=dict(min=0.1, median=0.3, p95=0.5, max=0.5),
        controller_wall_seconds=1.5, neural_ms=100.0, motor_nonzero_fraction=1.0,
        stationary_step_fraction=0.6, longest_stationary_streak=2,
        total_distance_pixels=6.0, unique_observation_count=2,
    )


def test_timeout_requires_full_episode_and_does_not_imply_movement():
    rows = [dict(before=asdict(State(48 * Q, 76 * Q, tick=i)),
                 after=asdict(State(48 * Q, 76 * Q, tick=i + 1,
                                   outcome="trial_timeout" if i + 1 == MAX_TICKS else None)),
                 action=action(), step_wall_seconds=0.2, observation_sha256="a" * 64)
            for i in range(MAX_TICKS)]
    result = summarize_trace(rows)
    assert result["outcome"] == "trial_timeout"
    assert result["stationary_step_fraction"] == 1
    assert result["motor_nonzero_fraction"] == 0
    assert result["longest_stationary_streak"] == MAX_TICKS
    assert result["total_distance_pixels"] == 0


@pytest.mark.parametrize("values, expected", [
    ([0.3], dict(min=0.3, median=0.3, p95=0.3, max=0.3)),
    (list(range(1, 21)), dict(min=1, median=10.5, p95=19, max=20)),
])
def test_latency_nearest_rank_and_small_samples(values, expected):
    assert latency_distribution(values) == expected


@pytest.mark.parametrize("values", [[], [float("nan")], [float("inf")], [-1], [True], ["0.1"]])
def test_latency_rejects_invalid_measurements(values):
    with pytest.raises(ValueError):
        latency_distribution(values)


@pytest.mark.parametrize("field, value", [
    ("step_wall_seconds", float("nan")), ("step_wall_seconds", float("inf")),
    ("step_wall_seconds", -0.1), ("step_wall_seconds", True),
    ("observation_sha256", "invalid"), ("observation_sha256", "g" * 64),
    ("action", {**action(), "dx": float("nan")}),
    ("action", {**action(), "dy": 1.1}),
    ("action", {**action(), "telemetry": {**action()["telemetry"], "neural_ms": float("inf")}}),
    ("before", dict(x_q=48 * Q, y_q=76 * Q, tick=True, outcome=None)),
])
def test_trace_rejects_corrupt_metrics(field, value):
    rows = trace()
    rows[0][field] = value
    with pytest.raises(ValueError):
        summarize_trace(rows)


@pytest.mark.parametrize("corruption", ["empty", "missing", "gap", "tick", "terminal", "timeout", "mode"])
def test_trace_rejects_incomplete_or_inconsistent_records(corruption):
    rows = trace()
    if corruption == "empty":
        rows = []
    elif corruption == "missing":
        del rows[1]["action"]
    elif corruption == "gap":
        rows.pop(1)
    elif corruption == "tick":
        rows[0]["after"]["tick"] = 2
    elif corruption == "terminal":
        rows[0]["after"]["outcome"] = rows[1]["before"]["outcome"] = "success"
    elif corruption == "timeout":
        rows[-1]["after"]["outcome"] = "trial_timeout"
    elif corruption == "mode":
        rows[-1]["action"]["model_mode"] = "windowed_reset"
    with pytest.raises(ValueError):
        summarize_trace(rows)


def test_total_latency_overflow_is_rejected():
    rows = trace()
    for row in rows:
        row["step_wall_seconds"] = 1e308
    with pytest.raises(ValueError, match="not finite"):
        summarize_trace(rows)


def probes():
    return [dict(seed=seed, condition=condition, action=action(),
                 observation_sha256=("0" if condition == "dark" else "1") * 64)
            for seed in (7, 11) for condition in ("dark", "bright")]


def test_distinct_pixels_do_not_automatically_prove_motor_sensitivity():
    records = probes()
    records[1]["action"]["telemetry"]["spike_count"] = 4
    result = summarize_visual_pairs(records)["comparisons"]["bright"]
    assert result["distinct_observation_pairs"] == 2
    assert result["motor_changed_pairs"] == 0
    assert result["telemetry_changed_pairs"] == 1
    assert result["max_motor_delta"] == 0


def test_visual_differences_use_matched_seeds_regardless_of_record_order():
    records = probes()
    records[1]["action"] = action(0.3, 0.4)
    records[3]["action"]["click"] = True
    summary = summarize_visual_pairs(records)
    assert summary == summarize_visual_pairs(reversed(records))
    result = summary["comparisons"]["bright"]
    assert result["seeds"] == [7, 11]
    assert result["motor_changed_fraction"] == 0.5
    assert result["max_motor_delta"] == 0.5
    assert result["mean_motor_delta"] == 0.25
    assert result["click_changed_pairs"] == 1


@pytest.mark.parametrize("corruption", ["empty", "missing", "duplicate", "seed", "mode", "digest"])
def test_visual_analysis_rejects_unmatched_or_corrupt_probes(corruption):
    records = deepcopy(probes())
    if corruption == "empty":
        records = []
    elif corruption == "missing":
        records.pop()
    elif corruption == "duplicate":
        records.append(deepcopy(records[0]))
    elif corruption == "seed":
        records[0]["seed"] = True
    elif corruption == "mode":
        records[1]["action"]["model_mode"] = "windowed_reset"
    elif corruption == "digest":
        records[0]["observation_sha256"] = ""
    with pytest.raises(ValueError):
        summarize_visual_pairs(records)
