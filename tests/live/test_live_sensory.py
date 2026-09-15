"""Synthetic graph mechanics only; real-model accounting belongs to its gate."""

import hashlib
from pathlib import Path

import numpy as np
import pytest

from flytrap.contracts import Observation
from flytrap.controllers.fly import FlyController, SEED_DOMAIN
from flytrap.lab.sensory import ResponseCapture, inspect_retina
from flytrap.live.sensory import CompiledRetina, LiveResponseCapture
from tests.controllers import conftest as synthetic_fixtures

adapter_files = synthetic_fixtures.adapter_files
adapter_files_factory = synthetic_fixtures.adapter_files_factory


def observation(offset=0):
    return Observation(schema_version="1", pixels=[((i + offset) % 256) / 255 for i in range(256)])


def test_compiled_mapping_matches_reference_for_different_inputs(adapter_files):
    controller = FlyController(**adapter_files)
    compiled = CompiledRetina(controller, annotations_path=adapter_files["annotations_path"])
    for sample in (observation(), observation(129), Observation(schema_version="1", pixels=[0.] * 256),
                   Observation(schema_version="1", pixels=[1.] * 256)):
        assert compiled.inspect(sample) == inspect_retina(
            controller, sample, annotations_path=adapter_files["annotations_path"])
    assert compiled.inspect(observation())["populations"]["L1"]["pixel_indices"] == [0, 10, 245, 255]


def test_cached_mapping_handles_missing_coordinates_and_duplicate_pixels(adapter_files_factory):
    from flytrap.controllers.fly import write_baseline_checkpoint

    def edit(annotations):
        annotations.loc[0, "assignedOlHex1"] = float("nan")
        annotations.loc[1, ["assignedOlHex1", "assignedOlHex2"]] = [0., 2.]

    files = adapter_files_factory(annotation_edit=edit)
    write_baseline_checkpoint(**files)
    controller = FlyController(**files)
    compiled = CompiledRetina(controller, annotations_path=files["annotations_path"])
    result = compiled.inspect(observation())
    assert result == inspect_retina(controller, observation(), annotations_path=files["annotations_path"])
    assert result["populations"]["L1"]["missing_coordinates"] == 1
    assert len(set(result["populations"]["L1"]["pixel_indices"])) == 2


def test_load_rejects_annotation_change_or_eye_mapping_tampering(adapter_files):
    controller = FlyController(**adapter_files)
    controller._eye.on_uv[0][1] = 0
    with pytest.raises(ValueError, match="raw-annotation sampling oracle"):
        CompiledRetina(controller, annotations_path=adapter_files["annotations_path"])
    with adapter_files["annotations_path"].open("ab") as stream:
        stream.write(b"modified")
    with pytest.raises(ValueError, match="annotations do not match"):
        CompiledRetina(controller, annotations_path=adapter_files["annotations_path"])


def test_passive_capture_preserves_fixture_outputs_seeds_and_has_zero_hot_path_io(adapter_files, monkeypatch):
    reference = FlyController(**adapter_files)
    live = FlyController(**adapter_files)
    compiled = CompiledRetina(live, annotations_path=adapter_files["annotations_path"])
    samples = [observation(), observation(127), observation(255)]
    expected = []
    reference.reset(run_seed=42, checkpoint=reference.checkpoint)
    for sample in samples:
        with ResponseCapture(reference, sample, annotations_path=adapter_files["annotations_path"]) as tap:
            output = reference.step(sample)
        expected.append((output, tap.rates, tap.statistics))
    live.reset(run_seed=42, checkpoint=live.checkpoint)
    seeds = []
    original_run = live._brain.run

    def run(*args, **kwargs):
        seeds.append(kwargs["seed"])
        return original_run(*args, **kwargs)

    monkeypatch.setattr(live._brain, "run", run)
    forbidden_reads = []

    def no_read(*args, **kwargs):
        forbidden_reads.append(str(args[0]) if args else "read")
        raise AssertionError("raw file access in the hot path")

    monkeypatch.setattr(Path, "read_bytes", no_read)
    monkeypatch.setattr("pandas.read_feather", no_read)
    monkeypatch.setattr("flytrap.live.sensory.file_sha256", no_read)
    monkeypatch.setattr("flytrap.lab.sensory.file_sha256", no_read)
    gains = live._gains.copy()
    weights = live._brain.wdata.copy()
    original_look, original_step = live._eye.look, live._pilot.step
    for sample, (reference_output, rates, statistics) in zip(samples, expected):
        with LiveResponseCapture(live, sample, retina=compiled) as tap:
            output = live.step(sample)
        assert output == reference_output
        assert tap.rates == rates
        assert tap.statistics == statistics
        assert tap.raw_action == {"dx": output.dx * 90, "dy": output.dy * 90, "click": output.click}
        assert live._eye.look == original_look
        assert live._pilot.step == original_step
    assert not forbidden_reads
    assert seeds == [int.from_bytes(hashlib.sha256(
        SEED_DOMAIN + (42).to_bytes(4, "big") + step.to_bytes(8, "big")).digest()[:8], "big")
        for step in range(len(samples))]
    np.testing.assert_array_equal(live._gains, gains)
    np.testing.assert_array_equal(live._brain.wdata, weights)
    assert not live._gains.flags.writeable


@pytest.mark.parametrize("tamper", ["pixels", "drive", "indices"])
def test_live_capture_rejects_boundary_tampering_before_neural_call(adapter_files, monkeypatch, tamper):
    controller = FlyController(**adapter_files)
    compiled = CompiledRetina(controller, annotations_path=adapter_files["annotations_path"])
    controller.reset(run_seed=7, checkpoint=controller.checkpoint)
    if tamper == "drive":
        controller._eye.on_uv[0][1] = 0
    elif tamper == "indices":
        controller._eye.on_idx[1] = 2
    calls = []
    monkeypatch.setattr(controller._brain, "run", lambda *a, **kw: calls.append(kw))
    sample = observation()
    original_look, original_step = controller._eye.look, controller._pilot.step
    with pytest.raises(ValueError, match="pixels differ|retinal drive|population indices"):
        with LiveResponseCapture(controller, sample, retina=compiled):
            controller.step(observation(1) if tamper == "pixels" else sample)
    assert calls == []
    assert controller._eye.look == original_look
    assert controller._pilot.step == original_step


def test_capture_cannot_nest_reuse_or_attach_to_other_controller(adapter_files):
    controller = FlyController(**adapter_files)
    compiled = CompiledRetina(controller, annotations_path=adapter_files["annotations_path"])
    controller.reset(run_seed=0, checkpoint=controller.checkpoint)
    sample = observation()
    tap = LiveResponseCapture(controller, sample, retina=compiled)
    with tap:
        with pytest.raises(RuntimeError, match="active or consumed"):
            with LiveResponseCapture(controller, sample, retina=compiled):
                pass
        controller.step(sample)
        with pytest.raises(RuntimeError, match="only one"):
            controller.step(sample)
    with pytest.raises(RuntimeError, match="active or consumed"):
        with tap:
            pass
    with pytest.raises(ValueError, match="different controller"):
        LiveResponseCapture(FlyController(**adapter_files), sample, retina=compiled)
