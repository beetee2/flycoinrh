"""Pure summaries for development evidence, without competence or learning claims.

Trace summaries validate recorded metrics and state continuity. They do not
replace replaying actions through the arena to verify physics and scoring.
Visual probes must reset the same model to each paired seed before the first
window; matching seeds alone does not establish matching model state.
"""

import math
from collections import defaultdict
from statistics import median

from flytrap.arena.core import Q, State
from flytrap.contracts import ControllerOutput


def _nonnegative_finite(value, name):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a finite nonnegative number")
    return float(value)


def _digest(value):
    if (type(value) is not str or len(value) != 64
            or any(char not in "0123456789abcdef" for char in value)):
        raise ValueError("Invalid observation_sha256")
    return value


def latency_distribution(values):
    """Seconds; p95 uses the empirical nearest-rank percentile, including n=1."""
    ordered = sorted(_nonnegative_finite(value, "latency") for value in values)
    if not ordered:
        raise ValueError("Cannot summarize empty latency measurements")
    return dict(min=ordered[0], median=median(ordered),
                p95=ordered[math.ceil(0.95 * len(ordered)) - 1], max=ordered[-1])


def summarize_trace(rows):
    """Summarize one development trace starting at tick zero.

    Every row contains before/after State dictionaries, a ControllerOutput
    dictionary, step_wall_seconds, and the observation_sha256 supplied to that
    action. An unfinished development trace retains outcome=None; it must not
    be reported as an arena timeout or successful completed episode.
    """
    rows = list(rows)
    if not rows:
        raise ValueError("Cannot summarize an empty trace")
    latencies, neural_times, distances = [], [], []
    observations = set()
    stationary = motor_nonzero = longest_streak = streak = 0
    previous = model_mode = None
    for index, row in enumerate(rows):
        try:
            before, after = State(**row["before"]), State(**row["after"])
            action = ControllerOutput.model_validate(row["action"])
            latency = _nonnegative_finite(row["step_wall_seconds"], "step_wall_seconds")
            digest = _digest(row["observation_sha256"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid trace row {index}: {exc}") from exc
        if index == 0 and before.tick != 0:
            raise ValueError("Trace must begin at tick zero")
        if previous is not None and before != previous:
            raise ValueError(f"Discontinuous trace at row {index}")
        if before.outcome is not None or after.tick != before.tick + 1:
            raise ValueError(f"Invalid terminal state or tick transition at row {index}")
        if model_mode is not None and action.model_mode != model_mode:
            raise ValueError("Trace mixes controller model modes")
        previous, model_mode = after, action.model_mode
        latencies.append(latency)
        neural_times.append(action.telemetry.neural_ms)
        observations.add(digest)
        motor_nonzero += action.dx != 0 or action.dy != 0
        distance = math.hypot(after.x_q - before.x_q, after.y_q - before.y_q) / Q
        distances.append(distance)
        if distance == 0:
            stationary += 1
            streak += 1
            longest_streak = max(longest_streak, streak)
        else:
            streak = 0
    try:
        wall_seconds = math.fsum(latencies)
    except OverflowError as exc:
        raise ValueError("Total wall time is not finite") from exc
    _nonnegative_finite(wall_seconds, "total wall time")
    return dict(
        steps=len(rows), environment_ticks=previous.tick, outcome=previous.outcome,
        step_latency_seconds=latency_distribution(latencies), controller_wall_seconds=wall_seconds,
        neural_ms=math.fsum(neural_times), motor_nonzero_fraction=motor_nonzero / len(rows),
        stationary_step_fraction=stationary / len(rows), longest_stationary_streak=longest_streak,
        total_distance_pixels=math.fsum(distances), unique_observation_count=len(observations),
    )


def summarize_visual_pairs(records, *, baseline_condition="dark"):
    """Compare complete first-window/reset probes paired by unsigned 32-bit seed.

    Records contain seed, condition, action (ControllerOutput), and
    observation_sha256. Duplicates or incomplete seed/condition sets are errors,
    preventing silent removal of missing or failed trials. Output differences
    measure sensitivity only; no learning or task-success inference is made.
    """
    grouped = defaultdict(dict)
    for record in records:
        try:
            seed, condition = record["seed"], record["condition"]
            if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
                raise ValueError("Invalid paired seed")
            if type(condition) is not str or not condition:
                raise ValueError("Invalid visual condition")
            action = ControllerOutput.model_validate(record["action"])
            digest = _digest(record["observation_sha256"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid visual record: {exc}") from exc
        if seed in grouped[condition]:
            raise ValueError("Duplicate visual condition/seed pair")
        grouped[condition][seed] = (action, digest)
    if baseline_condition not in grouped or len(grouped) < 2:
        raise ValueError("Require baseline and at least one comparison condition")
    baseline = grouped[baseline_condition]
    result = {}
    for condition in sorted(grouped):
        if condition == baseline_condition:
            continue
        probes = grouped[condition]
        if set(probes) != set(baseline):
            raise ValueError("Visual conditions must have identical complete seed sets")
        distinct_inputs = motor_changed = click_changed = telemetry_changed = 0
        deltas = []
        for seed in sorted(baseline):
            base_action, base_digest = baseline[seed]
            action, digest = probes[seed]
            if action.model_mode != base_action.model_mode:
                raise ValueError("Visual pair mixes controller model modes")
            distinct_inputs += digest != base_digest
            delta = math.hypot(action.dx - base_action.dx, action.dy - base_action.dy)
            deltas.append(delta)
            motor_changed += delta != 0
            click_changed += action.click != base_action.click
            telemetry_changed += action.telemetry != base_action.telemetry
        result[condition] = dict(
            pairs=len(baseline), seeds=sorted(baseline), distinct_observation_pairs=distinct_inputs,
            motor_changed_pairs=motor_changed, motor_changed_fraction=motor_changed / len(baseline),
            click_changed_pairs=click_changed, telemetry_changed_pairs=telemetry_changed,
            mean_motor_delta=math.fsum(deltas) / len(deltas), max_motor_delta=max(deltas),
        )
    return dict(baseline_condition=baseline_condition, comparisons=result)
