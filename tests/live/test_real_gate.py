"""The maintained real gate fails explicitly when real data is missing."""
import json

from flytrap.live import worker
from flytrap.live.accounting import LiveLedger
from scripts import live_real


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
