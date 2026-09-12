import json

import pytest
from hypothesis import given, strategies as st
from pydantic import ValidationError

from flytrap.contracts import ControllerOutput, Observation, RunRecord, RunRequest, canonical_sha256


@given(st.floats(min_value=0, max_value=1, allow_nan=False, allow_infinity=False))
def test_pixel_round_trip_preserves_numeric_value(pixel):
    observation = Observation(schema_version="1", pixels=[pixel] * 256)
    restored = Observation.model_validate_json(observation.model_dump_json())
    assert restored == observation


@given(st.one_of(st.integers(max_value=-1), st.integers(min_value=4294967296)))
def test_seed_bounds_are_rejected(seed):
    # Field-level validation through a complete RunRecord, including its checkpoint.
    record = {
        "schema_version": "1", "run_id": "run_a", "challenge_id": "challenge_a",
        "challenge_sha256": "a" * 64, "run_seed": seed, "config_sha256": "b" * 64,
        "controller_id": "fixture_v1", "checkpoint": {
            "schema_version": "1", "checkpoint_id": "fixture_v1", "sha256": "c" * 64,
            "graph_sha256": "d" * 64, "model_mode": "fixture",
        }, "state": "queued", "attempt": 0, "created_at_ms": 0,
        "started_at_ms": None, "finished_at_ms": None, "error_code": None,
    }
    with pytest.raises(ValidationError):
        RunRecord.model_validate(record)


@given(st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=30))
def test_paths_are_not_run_identifiers(component):
    for candidate in (f"../{component}", f"/{component}", f"{component}/file", f"https://{component}"):
        with pytest.raises(ValidationError):
            RunRequest(schema_version="1", challenge_id=candidate, controller_id="fixture_v1", checkpoint_id="fixture_v1")


@given(st.floats(allow_nan=False, allow_infinity=False).filter(lambda value: abs(value) > 1))
def test_unbounded_action_rejected(action):
    with pytest.raises(ValidationError):
        ControllerOutput(schema_version="1", dx=action, dy=0.0, click=False, model_mode="fixture", telemetry={
            "schema_version": "1", "sampled_neurons": 2, "spike_count": 1, "neural_ms": 1.0,
        })


@given(st.dictionaries(st.text(alphabet="abcdef", min_size=1, max_size=8), st.integers(), max_size=10))
def test_canonical_hash_stable_across_serialization_and_key_order(payload):
    reversed_payload = dict(reversed(list(payload.items())))
    assert canonical_sha256(payload) == canonical_sha256(reversed_payload)
    assert canonical_sha256(payload) == canonical_sha256(json.loads(json.dumps(payload)))
