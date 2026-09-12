"""P00 synthetic unit contracts and accounting; no full-model calls are made."""

import copy
import hashlib
import json

import pytest
from pydantic import ValidationError

from flytrap.lab.budget import BudgetExceeded, CallBudget
from flytrap.lab.contracts import CALL_CAP, MOTORS, SEEDS, LabRequest, LabResult
from flytrap.lab.runner import summarize

pytestmark = [pytest.mark.unit, pytest.mark.contract]


def synthetic_request():
    return dict(schema_version="flytrap-lab-request-1", a=[0] * 256, b=[255] * 256)


def synthetic_result():
    """Schema specimen only, never recorded or presented as real inference evidence."""
    request = LabRequest.model_validate(synthetic_request())
    population = dict(neuron_indices=[0], body_ids=[1], pixel_indices=[0], sampled_pixels_u8=[0],
                      drive_hz=[0.0], coverage_counts=[1] + [0] * 255, missing_coordinates=0)
    retina = dict(populations={"L1": copy.deepcopy(population), "L2": copy.deepcopy(population)},
                  union_coverage_counts=[2] + [0] * 255, sampled_pixel_count=1,
                  discarded_pixel_indices=list(range(1, 256)))
    retina_b = copy.deepcopy(retina)
    for pop in retina_b["populations"].values():
        pop["sampled_pixels_u8"] = [255]
    samples = [dict(side=side, seed=seed, motor_rates_hz={motor: 0.0 for motor in MOTORS},
                    statistics=dict(sampled_neurons=1, spike_count=0, firing=0, spikes_per_sec=0.0,
                                    mean_mv=-60.0, visual=0, motor=0), neural_ms=20.0)
               for seed in SEEDS for side in ("A", "A_repeat", "B")]
    return copy.deepcopy(dict(schema_version="flytrap-lab-result-1", result_id="a" * 32,
                              created_at="2026-09-11T00:00:00+00:00", cached=False, fixture=False,
                              request=request.model_dump(), seeds=list(SEEDS), samples=samples,
                              retina={"A": retina, "B": retina_b}, comparison=summarize(request, samples),
                              identities=dict(model={"test_specimen": "synthetic; not model evidence"},
                                              graph_manifest_sha256="0" * 64, source_head="0" * 40,
                                              source_sha256={"synthetic.py": "0" * 64},
                                              source_tree_sha256="0" * 64,
                                              runtime={"test_specimen": "synthetic"},
                                              input_sha256={side: hashlib.sha256(bytes(pixels)).hexdigest()
                                                            for side, pixels in (("A", request.a), ("B", request.b))},
                                              encoding="synthetic", comparison="synthetic", statistics="synthetic",
                                              limitations="Synthetic test specimen; no model evidence"), attempted_calls=9))


@pytest.mark.parametrize("length", [0, 255, 257, 8192])
def test_input_pixel_count_is_exact(length):
    request = synthetic_request()
    request["a"] = [0] * length
    with pytest.raises(ValidationError):
        LabRequest.model_validate(request)


@pytest.mark.parametrize("value", [-1, 256, True, False, 1.5, 1.0, "1", None, float("nan"), float("inf")])
@pytest.mark.parametrize("side", ["a", "b"])
def test_inputs_are_strict_uint8(side, value):
    request = synthetic_request()
    request[side][7] = value
    with pytest.raises(ValidationError):
        LabRequest.model_validate(request)


@pytest.mark.parametrize("field,value", [("seeds", [1]), ("steps", 100), ("checkpoint", "candidate"),
                                         ("goal", [2, 3]), ("schema_version", "1")])
def test_request_cannot_override_declared_work_or_model(field, value):
    request = synthetic_request()
    request[field] = value
    with pytest.raises(ValidationError):
        LabRequest.model_validate(request)


def test_request_round_trip_preserves_every_submitted_pixel():
    request = synthetic_request()
    request["a"] = list(range(256))
    request["b"] = list(reversed(range(256)))
    assert LabRequest.model_validate_json(json.dumps(request)).model_dump() == request


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
@pytest.mark.parametrize("location", ["rate", "statistic", "drive", "delta", "paired_delta"])
def test_result_rejects_nonfinite_measurements(location, value):
    result = synthetic_result()
    targets = {
        "rate": (result["samples"][0]["motor_rates_hz"], "click"),
        "statistic": (result["samples"][0]["statistics"], "mean_mv"),
        "drive": (result["retina"]["A"]["populations"]["L1"]["drive_hz"], 0),
        "delta": (result["comparison"]["motor_rates_hz"]["click"], "delta_mean"),
        "paired_delta": (result["comparison"]["motor_rates_hz"]["click"]["paired_deltas"], 0),
    }
    container, key = targets[location]
    container[key] = value
    with pytest.raises(ValidationError):
        LabResult.model_validate(result)


@pytest.mark.parametrize("field", ["neuron_indices", "body_ids", "pixel_indices", "sampled_pixels_u8", "drive_hz"])
def test_result_retinal_arrays_must_align(field):
    result = synthetic_result()
    result["retina"]["A"]["populations"]["L1"][field].append(0)
    with pytest.raises(ValidationError, match="retinal arrays must align"):
        LabResult.model_validate(result)


@pytest.mark.parametrize("mutation", ["seed_order", "duplicate_seed", "missing_sample", "wrong_pair", "unknown"])
def test_result_requires_all_fixed_matched_repeats(mutation):
    result = synthetic_result()
    if mutation == "seed_order":
        result["seeds"].reverse()
    elif mutation == "duplicate_seed":
        result["seeds"][1] = 17
    elif mutation == "missing_sample":
        result["samples"].pop()
    elif mutation == "wrong_pair":
        result["samples"][2]["side"] = "A"
    else:
        result["samples"][0]["recognition"] = True
    with pytest.raises(ValidationError):
        LabResult.model_validate(result)


def test_result_json_round_trip():
    result = LabResult.model_validate(synthetic_result())
    assert LabResult.model_validate_json(result.model_dump_json()) == result


def test_summary_separates_repeatability_from_across_seed_variation():
    specimen = synthetic_result()
    for index, sample in enumerate(specimen["samples"]):
        sample["motor_rates_hz"]["click"] = 1.0 + index // 3 + (2 if sample["side"] == "B" else 0)
    request = LabRequest.model_validate(specimen["request"])
    result = summarize(request, specimen["samples"])
    assert result["same_seed_repeatable"] is True
    assert result["motor_rates_hz"]["click"] == dict(a_mean=2.0, b_mean=4.0, a_sd=1.0, b_sd=1.0,
                                                      delta_mean=2.0, delta_sd=0.0, paired_deltas=[2.0] * 3)
    specimen["samples"][1]["statistics"]["spike_count"] = 1
    assert summarize(request, specimen["samples"])["same_seed_repeatable"] is False


def test_summary_declares_equal_brightness_and_same_image_separately():
    specimen = synthetic_result()
    request = LabRequest.model_validate(synthetic_request())
    request.a = [255] * 128 + [0] * 128
    request.b = [0] * 128 + [255] * 128
    result = summarize(request, specimen["samples"])
    assert result["same_image"] is False
    assert result["equal_brightness"] is True
    assert result["mean_brightness_u8"] == {"A": 127.5, "B": 127.5}
    request.b = request.a.copy()
    assert summarize(request, specimen["samples"])["same_image"] is True


def test_ledger_counts_attempt_before_failure_and_stops_at_cap(tmp_path):
    budget = CallBudget(tmp_path / "attempts.jsonl")
    assert budget.attempted == 0
    with pytest.raises(RuntimeError, match="synthetic inference failure"):
        budget.record_attempt(result_id="specimen", seed=17, side="A")
        raise RuntimeError("synthetic inference failure")
    assert CallBudget(budget.path).attempted == 1
    for _ in range(CALL_CAP - 1):
        budget.record_attempt(result_id="specimen", seed=17, side="A")
    before = budget.path.read_bytes()
    with pytest.raises(BudgetExceeded):
        budget.record_attempt(result_id="specimen", seed=17, side="A")
    assert budget.attempted == CALL_CAP
    assert budget.path.read_bytes() == before


@pytest.mark.parametrize("content", ["not json\n", '{}\n', '[]\n', 'null\n', '{"attempt":true}\n',
                                     '{"attempt":2}\n', '{"attempt":1}\n{"attempt":1}\n',
                                     '{"attempt":1}\n\n'])
def test_corrupted_ledger_fails_closed_without_append(tmp_path, content):
    budget = CallBudget(tmp_path / "attempts.jsonl")
    budget.path.write_text(content)
    with pytest.raises(ValueError):
        budget.record_attempt(result_id="specimen", seed=17, side="A")
    assert budget.path.read_text() == content


@pytest.mark.parametrize("field", ["model", "graph_manifest_sha256", "source_head", "source_sha256", "source_tree_sha256",
                                 "runtime", "input_sha256", "encoding", "comparison", "statistics", "limitations"])
def test_result_rejects_missing_provenance(field):
    result = synthetic_result()
    del result["identities"][field]
    with pytest.raises(ValidationError):
        LabResult.model_validate(result)


@pytest.mark.parametrize("field", ["graph_manifest_sha256", "source_head", "source_tree_sha256"])
def test_result_rejects_invalid_provenance_digest(field):
    result = synthetic_result()
    result["identities"][field] = "not-a-digest"
    with pytest.raises(ValidationError):
        LabResult.model_validate(result)


@pytest.mark.parametrize("mutation,match", [
    ("histogram", "coverage counts must match"),
    ("union", "combined coverage"),
    ("sampled_count", "sampled pixel count"),
    ("discarded_missing", "ordered coverage complement"),
    ("discarded_duplicate", "ordered coverage complement"),
    ("discarded_order", "ordered coverage complement"),
    ("sample_bytes", "samples must match submitted"),
    ("input_hash", "input hash must identify"),
    ("same_image", "comparison controls"),
    ("equal_brightness", "comparison controls"),
    ("mean_brightness_a", "comparison controls"),
    ("mean_brightness_b", "comparison controls"),
])
def test_result_rejects_semantically_inconsistent_display_data(mutation, match):
    result = synthetic_result()
    retina = result["retina"]["B"]
    if mutation == "histogram":
        retina["populations"]["L1"]["coverage_counts"][0] = 2
    elif mutation == "union":
        retina["union_coverage_counts"][0] = 1
    elif mutation == "sampled_count":
        retina["sampled_pixel_count"] = 2
    elif mutation == "discarded_missing":
        retina["discarded_pixel_indices"].pop()
    elif mutation == "discarded_duplicate":
        retina["discarded_pixel_indices"][1] = 1
    elif mutation == "discarded_order":
        retina["discarded_pixel_indices"].reverse()
    elif mutation == "sample_bytes":
        retina["populations"]["L1"]["sampled_pixels_u8"][0] = 0
    elif mutation == "input_hash":
        result["identities"]["input_sha256"]["B"] = "0" * 64
    elif mutation in ("same_image", "equal_brightness"):
        result["comparison"][mutation] = True
    else:
        result["comparison"]["mean_brightness_u8"][mutation[-1].upper()] = 127.5
    with pytest.raises(ValidationError, match=match):
        LabResult.model_validate(result)


@pytest.mark.parametrize("field", ["neuron_indices", "body_ids", "pixel_indices", "missing_coordinates"])
def test_result_requires_identical_a_b_retinal_mapping(field):
    result = synthetic_result()
    retina = result["retina"]["B"]
    population = retina["populations"]["L1"]
    if field == "missing_coordinates":
        population[field] = 1
    else:
        population[field][0] += 1
    if field == "pixel_indices":
        population["coverage_counts"] = [0, 1] + [0] * 254
        retina["union_coverage_counts"] = [1, 1] + [0] * 254
        retina["sampled_pixel_count"] = 2
        retina["discarded_pixel_indices"] = list(range(2, 256))
    with pytest.raises(ValidationError, match="identical retinal mapping"):
        LabResult.model_validate(result)
