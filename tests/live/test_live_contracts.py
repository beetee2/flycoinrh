"""Cross-language synthetic contract corpus and Python-specific invalid values."""
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from flytrap.live.contracts import FlightControls, FrameIdentity, SessionConfig
from flytrap.live.wire_contracts import CONTRACTS
from scripts.live_contract_examples import corpus


@pytest.mark.parametrize("case", corpus(), ids=lambda case: case["name"])
def test_shared_wire_corpus(case):
    model = CONTRACTS[case["contract"]]
    payload = json.dumps(case["value"])
    if case["valid"]:
        assert json.loads(model.model_validate_json(payload).model_dump_json()) == case["value"]
    else:
        with pytest.raises(ValidationError):
            model.model_validate_json(payload)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), "1", True])
def test_nonfinite_and_coerced_control_numbers(value):
    payload = next(c["value"] for c in corpus() if c["contract"] == "FlightControls")
    payload["yaw_rate_rad_s"] = value
    with pytest.raises(ValidationError):
        FlightControls.model_validate(payload)


def test_python_rejects_coerced_epoch_and_mutation():
    payload = next(c["value"] for c in corpus() if c["contract"] == "FrameIdentity")
    payload["generation"] = 1.0
    with pytest.raises(ValidationError):
        FrameIdentity.model_validate(payload)
    config = SessionConfig(source_id="fixture", evidence_kind="fixture", seed=0)
    assert config.recording is False
    with pytest.raises(ValidationError):
        config.recording = True


def test_generated_schema_and_corpus_match_python():
    root = Path("web/src/live/generated")
    assert json.loads((root / "schemas.json").read_text()) == {
        name: model.model_json_schema() for name, model in CONTRACTS.items()}
    assert json.loads((root / "examples.json").read_text()) == corpus()
