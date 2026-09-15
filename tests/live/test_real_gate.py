"""The maintained real gate fails explicitly when real data is missing."""
import json

from flytrap.live import worker
from flytrap.live.accounting import LiveLedger
from scripts import live_real


def test_terminal_flight_snapshot_can_be_saved_as_real_gate_evidence():
    from flytrap.live.neural import SessionSnapshot
    from flytrap.live.flight import initial_state
    from flytrap.live.wire_contracts import CONTRACTS
    from scripts.live_contract_examples import corpus
    status = next(row["value"] for row in corpus() if row["contract"] == "SessionStatus" and row["valid"])
    snapshot = SessionSnapshot(status=CONTRACTS["SessionStatus"].model_validate(status),
        sample=None, last_inferred=None, last_completed=None, waiting_for_sample=True,
        completed_calls=0, rejected_results=0, neural_ms=20., model_hz=0., last_step_wall_ms=None,
        source_receipt_age_ms=None, model_kind="fixture",
        flight=initial_state(status["session_id"], status["generation"], "fixture").snapshot)
    encoded = json.loads(json.dumps(live_real.snapshot_json(snapshot), allow_nan=False))
    assert encoded["flight"]["position"] == [0., 0., 2.]
    assert encoded["flight"]["session_id"] == encoded["status"]["session_id"]


def test_missing_real_data_is_blocked_nonzero_without_charging_or_substituting(tmp_path, monkeypatch):
    files = worker.model_files()
    files["graph_root"] = worker.REPOSITORY / "build/obs02-deliberately-missing-test-graph"
    monkeypatch.setattr(worker, "model_files", lambda *args: files)

    def forbidden(*args, **kwargs):
        raise AssertionError("missing data must fail before any model call/accounting")

    monkeypatch.setattr(LiveLedger, "record_attempt", forbidden)
    output = tmp_path / "missing-data-evidence"
    assert live_real.main(["--output", str(output)]) == 2
    report = json.loads((output / "result.json").read_text())
    assert report["status"] == "BLOCKED"
    assert "Missing real model prerequisites" in report["reason"]
    assert "live_final" not in report
