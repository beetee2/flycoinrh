import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from flytrap.contracts import (
    CONTRACTS, Observation, RunRecord, canonical_sha256, create_challenge,
    verify_challenge_hash,
)
from scripts.generate_contracts import OUTPUT, generate

CASES_PATH = Path(__file__).resolve().parents[1] / "fixtures/contracts/cases.json"
CASES = json.loads(CASES_PATH.read_text())
SCHEMAS = json.loads(OUTPUT.read_text())


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_shared_wire_cases(case):
    model = CONTRACTS[case["contract"]]
    raw = json.dumps(case["payload"], allow_nan=False)
    assert Draft202012Validator(SCHEMAS[case["contract"]]).is_valid(case["payload"]) == case["valid"]
    if case["valid"]:
        parsed = model.model_validate_json(raw)
        assert model.model_validate_json(parsed.model_dump_json()) == parsed
    else:
        with pytest.raises(ValidationError):
            model.model_validate_json(raw)


def test_every_contract_has_valid_and_invalid_cross_language_cases():
    for contract in CONTRACTS:
        assert {case["valid"] for case in CASES if case["contract"] == contract} == {True, False}


def test_generated_schema_is_current():
    assert OUTPUT.read_text() == generate()
    for schema in SCHEMAS.values():
        Draft202012Validator.check_schema(schema)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_observation_rejected(value):
    payload = {"schema_version": "1", "pixels": [0.0] * 256}
    payload["pixels"][42] = value
    with pytest.raises(ValidationError):
        Observation.model_validate(payload)


@pytest.mark.parametrize("field", ["goal", "target", "score", "challenge", "seed", "tick", "position"])
def test_observation_forbids_privileged_fields(field):
    payload = {"schema_version": "1", "pixels": [0.0] * 256, field: 1}
    with pytest.raises(ValidationError):
        Observation.model_validate(payload)


def test_canonical_hash_ignores_object_key_order_and_rejects_nan():
    assert canonical_sha256({"b": 2, "a": 1}) == canonical_sha256({"a": 1, "b": 2})
    assert canonical_sha256({"a": 1}) != canonical_sha256({"a": 2})
    with pytest.raises(ValueError):
        canonical_sha256({"a": float("nan")})


def test_unknown_fields_rejected_inside_nested_models():
    valid = next(case for case in CASES if case["contract"] == "ControllerOutput" and case["valid"])
    payload = copy.deepcopy(valid["payload"])
    payload["telemetry"]["goal_x"] = 10
    with pytest.raises(ValidationError):
        CONTRACTS["ControllerOutput"].model_validate(payload)


def numeric_paths(value, prefix=()):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from numeric_paths(child, (*prefix, key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from numeric_paths(child, (*prefix, index))
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        yield prefix


NUMERIC_CASES = [
    (case, path) for case in CASES if case["valid"]
    for path in numeric_paths(case["payload"])
]


@pytest.mark.parametrize("case,path", NUMERIC_CASES)
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_every_numeric_field_rejects_nonfinite(case, path, value):
    payload = copy.deepcopy(case["payload"])
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValidationError):
        CONTRACTS[case["contract"]].model_validate(payload)


def test_integer_exponent_json_notation_matches_json_schema():
    case = next(case for case in CASES if case["name"] == "RunRecord integer decimal notation")
    raw = json.dumps(case["payload"]).replace('"run_seed": 1.0', '"run_seed": 1e0')
    assert RunRecord.model_validate_json(raw).run_seed == 1


def test_challenge_content_hash_is_computed_and_tampering_rejected():
    case = next(case for case in CASES if case["contract"] == "ChallengeSpec" and case["valid"])
    content = {key: value for key, value in case["payload"].items() if key != "content_sha256"}
    challenge = create_challenge(content)
    assert challenge.content_sha256 == case["payload"]["content_sha256"]
    verify_challenge_hash(challenge)
    tampered = challenge.model_copy(update={"destination_side": "right"})
    with pytest.raises(ValueError, match="mismatch"):
        verify_challenge_hash(tampered)
    with pytest.raises(ValueError, match="computed by the server"):
        create_challenge(case["payload"])
