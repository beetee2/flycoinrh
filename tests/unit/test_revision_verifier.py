"""Synthetic scripted artifacts validate mechanics and cannot pass the real gate."""

from copy import deepcopy
from dataclasses import asdict
import json

from PIL import Image
import pytest

from flytrap.arena.core import build_arena, initial_state, step
from flytrap.arena.render import png_bytes, render
from flytrap.arena.sliding import step_sliding
from flytrap.contracts import ControllerOutput
from scripts.feasibility import overlay
from scripts.feasibility_revision import observe, pad_samples, sample_coordinates, schedule
from scripts.verify_feasibility import _challenge, _file_sha, _object_sha, _sha
from scripts.verify_feasibility_revision import _preregistration, _sources, verify, verify_trial, verify_trials

pytestmark = pytest.mark.unit


def save(path, value):
    path.write_text(json.dumps(value, allow_nan=False) + "\n")


@pytest.fixture
def fixture_artifacts(tmp_path):
    """No neural calls: labeled fixture with prescribed downward motion to a wall."""
    config = dict(physics=["no_sliding_v1", "tangent_v2"], seeds=[7], layouts=["left", "right"],
                  inputs=["canonical", "dark"], primary_crop="crop16_v1", optional_crop="overview16_v2",
                  primary_episodes=8, optional_episodes=4, diagnostic_tick_limit=20)

    def create(stage="physics"):
        trials = schedule(config, stage)
        for trial in trials:
            directory = tmp_path / trial["id"]
            directory.mkdir()
            arena = build_arena(_challenge(trial["layout"]))
            raster = render(arena.scene)
            (directory / "canonical.gray").write_bytes(raster)
            (directory / "canonical.png").write_bytes(png_bytes(raster))
            state, rows = initial_state(), []
            for _ in range(config["diagnostic_tick_limit"]):
                obs = observe(raster, state, trial["crop"], trial["input"])
                pixels = bytes(round(value*255) for value in obs.pixels)
                action = ControllerOutput(schema_version="1", dx=0.05, dy=1.0, click=False, model_mode="fixture",
                    telemetry=dict(schema_version="1", sampled_neurons=0, spike_count=0, neural_ms=0.0))
                physics = step if trial["physics"] == "no_sliding_v1" else step_sliding
                after = physics(arena, state, action)
                xs, ys = sample_coordinates(state, trial["crop"])
                rows.append(dict(before=asdict(state), after=asdict(after), action=action.model_dump(),
                    raw_action=action.model_dump(), motor_rates=dict(steer_L=0.0, steer_R=22.5, fwd_L=0.0,
                    fwd_R=0.0, back=450.0, stop=0.0), step_wall_seconds=0.01,
                    observation_pixels=list(pixels), observation_sha256=_sha(pixels), sample_xs=xs, sample_ys=ys,
                    pad_sample_count=pad_samples(arena, state, trial["crop"])))
                if state.tick in (0, 16, 32, 64, 95):
                    Image.frombytes("L", (16, 16), pixels).save(directory / f"input-{state.tick:03}.png")
                state = after
            (directory / "trace.jsonl").write_text("".join(json.dumps(row)+"\n" for row in rows))
            overlay(directory / "trajectory.png", raster, rows, "SYNTHETIC VERIFIER FIXTURE")
            trial.update(status="PASS", ticks=len(rows), final_state=asdict(state), outcome=None,
                         termination="diagnostic_cutoff", elapsed_wall_seconds=1.0,
                         cue_free_ticks=sum(row["pad_sample_count"] == 0 for row in rows),
                         trace_sha256=_file_sha(directory / "trace.jsonl"))
        return config, trials, tmp_path
    return create


@pytest.mark.parametrize("stage", ["physics", "overview"])
def test_full_fixture_schedule_replays_pixels_rates_physics_and_images(fixture_artifacts, stage):
    config, trials, root = fixture_artifacts(stage)
    result = verify_trials(trials, root, config, stage, require_real=False)
    assert result["trials"] == len(trials)
    assert result["steps"] == len(trials)*20
    with pytest.raises(ValueError, match="real/fixture"):
        verify_trial(trials[0], root, config)


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "seed", "physics", "crop", "failed", "order"])
def test_missing_changed_or_failed_scheduled_trials_fail(fixture_artifacts, mutation):
    config, trials, root = fixture_artifacts()
    if mutation == "missing":
        trials.pop()
    elif mutation == "duplicate":
        trials[1] = deepcopy(trials[0])
    elif mutation == "seed":
        trials[0]["seed"] += 1
    elif mutation in ("physics", "crop"):
        trials[0][mutation] = "unknown_v99"
    elif mutation == "failed":
        trials[0]["status"] = "FAIL"
    else:
        trials.reverse()
    with pytest.raises(ValueError):
        verify_trials(trials, root, config, "physics", require_real=False)


@pytest.mark.parametrize("mutation", ["raw", "rates", "nan_rate", "coordinates", "pixels", "hash", "before",
                                     "after", "pad_samples", "negative_runtime", "extra_step"])
def test_redigested_trace_tampering_still_fails(fixture_artifacts, mutation):
    config, trials, root = fixture_artifacts()
    trial = trials[0]
    path = root / trial["id"] / "trace.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    row = rows[0]
    if mutation == "raw":
        row["raw_action"]["dx"] = 0.9
    elif mutation == "rates":
        row["motor_rates"]["back"] = 0
    elif mutation == "nan_rate":
        row["motor_rates"]["back"] = float("nan")
    elif mutation == "coordinates":
        row["sample_ys"][0] += 1
    elif mutation == "pixels":
        row["observation_pixels"][0] ^= 255
    elif mutation == "hash":
        row["observation_sha256"] = "0"*64
    elif mutation in ("before", "after"):
        row[mutation]["x_q"] += 1
    elif mutation == "pad_samples":
        row["pad_sample_count"] += 1
    elif mutation == "negative_runtime":
        row["step_wall_seconds"] = -1
    else:
        rows.append(deepcopy(rows[-1]))
    path.write_text("".join(json.dumps(row)+"\n" for row in rows))
    trial["trace_sha256"] = _file_sha(path)
    with pytest.raises(ValueError):
        verify_trial(trial, root, config, require_real=False)


@pytest.mark.parametrize("mutation", ["timeout", "outcome", "ticks", "cue_summary", "runtime", "digest",
                                     "missing_input", "input", "trajectory", "canonical"])
def test_summary_or_image_tampering_fails(fixture_artifacts, mutation):
    config, trials, root = fixture_artifacts()
    trial = trials[0]
    directory = root / trial["id"]
    if mutation == "timeout":
        trial["termination"] = "trial_timeout"
    elif mutation == "outcome":
        trial["outcome"] = "success"
    elif mutation == "ticks":
        trial["ticks"] -= 1
    elif mutation == "cue_summary":
        trial["cue_free_ticks"] += 1
    elif mutation == "runtime":
        trial["elapsed_wall_seconds"] = 0
    elif mutation == "digest":
        trial["trace_sha256"] = "0"*64
    elif mutation == "missing_input":
        (directory / "input-000.png").unlink()
    elif mutation == "input":
        Image.new("L", (16, 16), 17).save(directory / "input-000.png")
    elif mutation == "trajectory":
        Image.new("RGB", (576, 666), "red").save(directory / "trajectory.png")
    else:
        (directory / "canonical.gray").write_bytes(bytes(96*96))
    with pytest.raises((ValueError, OSError)):
        verify_trial(trial, root, config, require_real=False)


def test_real_gate_rejects_fixture_and_missing_artifacts(tmp_path):
    with pytest.raises(ValueError, match="missing"):
        verify(tmp_path)
    save(tmp_path / "report.json", {"fixture": True})
    save(tmp_path / "config.json", {})
    with pytest.raises(ValueError, match="Fixture"):
        verify(tmp_path, config_path=tmp_path / "config.json")


@pytest.mark.parametrize("mutation", ["digest", "source", "omitted_version"])
def test_source_version_identity_cannot_be_changed(tmp_path, mutation):
    path = tmp_path / "physics_v2.py"
    path.write_text("synthetic dependency version 2")
    mapping = {str(path): _file_sha(path)}
    source = dict(file_sha256=mapping, source_tree_sha256=_object_sha(mapping))
    _sources(source, [str(path)])
    if mutation == "digest":
        source["source_tree_sha256"] = "0"*64
    elif mutation == "source":
        path.write_text("different version")
    else:
        source["file_sha256"] = {}
        source["source_tree_sha256"] = _object_sha({})
    with pytest.raises(ValueError):
        _sources(source, [str(path)])


@pytest.mark.parametrize("mutation", ["config", "digest", "after_start", "no_timezone"])
def test_preregistration_must_match_and_precede_execution(tmp_path, mutation):
    output = tmp_path / "primary"
    output.mkdir()
    config = {"synthetic_fixture_only": True, "budget": 2}
    report = dict(config_sha256="a"*64, started_utc="2026-09-12T00:00:01+00:00")
    declaration = dict(config=config.copy(), config_sha256="a"*64, declared_utc="2026-09-12T00:00:00+00:00")
    save(tmp_path / "preregistration.json", declaration)
    _preregistration(output, report, config)
    if mutation == "config":
        declaration["config"]["budget"] = 999
    elif mutation == "digest":
        declaration["config_sha256"] = "b"*64
    elif mutation == "after_start":
        declaration["declared_utc"] = "2026-09-12T00:00:02+00:00"
    else:
        declaration["declared_utc"] = "2026-09-12T00:00:00"
    save(tmp_path / "preregistration.json", declaration)
    with pytest.raises(ValueError):
        _preregistration(output, report, config)
