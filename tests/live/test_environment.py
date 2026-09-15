"""Host-independent metadata discovery and bounded diagnostic regressions."""
import json
from pathlib import Path
import sys

import pytest

from flytrap.live import environment
from flytrap.live.__main__ import main
from flytrap.live.contracts import SourceCapability


def test_missing_sysfs_reports_blocked_without_capture(tmp_path):
    report = environment.discover_devices(tmp_path / "missing", tmp_path / "dev")
    assert report["status"] == "blocked"
    assert report["devices"] == []
    assert report["capture_started"] is False


def test_discovery_reads_metadata_and_never_opens_device(tmp_path, monkeypatch):
    sysfs, dev = tmp_path / "sysfs", tmp_path / "dev"
    device = sysfs / "video7"
    (device / "device").mkdir(parents=True)
    dev.mkdir()
    (device / "name").write_text("Operator OBS camera\n")
    (device / "device/uevent").write_text("DRIVER=v4l2loopback\n")
    # /dev/null is only stat'ed; no hardware or privileged mknod is needed.
    (dev / "video7").symlink_to("/dev/null")
    original_open = Path.open

    def checked_open(self, *args, **kwargs):
        assert self.parent != dev, "discovery opened a device"
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", checked_open)
    monkeypatch.setattr(environment.subprocess, "Popen", lambda *a, **k: pytest.fail("discovery launched capture"))
    report = environment.discover_devices(sysfs, dev)
    assert report["status"] == "ok"
    source, = report["devices"]
    assert source["source_id"] == "v4l2-video7"
    assert source["driver"] == "v4l2loopback"
    assert source["name"] == "Operator OBS camera"
    assert source["capabilities"] is None and source["formats"] is None
    assert source["selected"] is False
    capability = SourceCapability.model_validate(source["capability"])
    assert capability.evidence_kind == "real"
    assert capability.producer_detection == "unknown"
    assert capability.metadata_state == "partial"
    assert report["real_obs_gate"] == "not_run"


def test_sysfs_labels_are_bounded_and_printable(tmp_path):
    device = tmp_path / "sysfs/video1"
    (device / "device").mkdir(parents=True)
    (device / "name").write_text("OBS\x00\n" + "x" * 180)
    (device / "device/uevent").write_text("DRIVER=test\x1bdriver\n")
    report = environment.discover_devices(tmp_path / "sysfs", tmp_path / "missing")
    capability = SourceCapability.model_validate(report["devices"][0]["capability"])
    assert len(capability.name) == 128
    assert capability.driver == "testdriver"
    assert capability.name.isprintable()
    assert report["real_obs_gate"] == "not_run"


def test_regular_file_is_not_a_capture_device(tmp_path):
    device = tmp_path / "sysfs/video0"
    device.mkdir(parents=True)
    (device / "name").write_text("Physical camera")
    dev = tmp_path / "dev"
    dev.mkdir()
    (dev / "video0").write_bytes(b"not a character device")
    report = environment.discover_devices(tmp_path / "sysfs", dev)
    assert report["status"] == "blocked"
    assert report["devices"][0]["character_device"] is False


def test_sysfs_permission_failure_is_explicit(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "iterdir", lambda _: (_ for _ in ()).throw(PermissionError()))
    report = environment.discover_devices(tmp_path)
    assert report["status"] == "blocked"
    assert "inaccessible" in report["errors"][0]


@pytest.mark.parametrize("script,status", [
    ("raise SystemExit(9)", "failed"),
    ("import time; time.sleep(10)", "timeout"),
    ("import sys; sys.stdout.write('x' * 1000000)", "output_limit"),
])
def test_metadata_subprocess_failure_is_bounded(script, status):
    report = environment.metadata_command([sys.executable, "-c", script], timeout=0.15)
    assert report["status"] == status
    assert report["exit_code"] is not None
    assert len(report["output"]) <= environment.MAX_METADATA_BYTES


def test_missing_tool_has_actionable_state(monkeypatch):
    monkeypatch.setattr(environment.shutil, "which", lambda _: None)
    report = environment.metadata_command(["ffmpeg", "-version"])
    assert report["status"] == "missing"
    assert report["exit_code"] is None


def test_missing_data_is_blocked_without_model_import(tmp_path, monkeypatch):
    import builtins
    original_import = builtins.__import__

    def no_model_import(name, *args, **kwargs):
        assert name not in ("flysim", "flyeye", "flytrap.controllers.fly")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_model_import)
    report = environment.inspect_model_identity(tmp_path)
    assert report["status"] == "blocked"
    assert report["model_loaded"] is False
    assert report["neural_calls"] == 0
    assert any("Missing or unreadable graph" in error for error in report["errors"])


def test_model_identity_rejects_changed_sources_and_fixture_catalog(tmp_path, monkeypatch):
    # Synthetic metadata tests the audit itself; it is never real-model evidence.
    fingerprint = "a" * 64
    checkpoint = {
        "fixture": False, "neural_state_mode": "windowed_reset", "learning_enabled": False,
        "gains": "all-one-float32", "model_source_sha256": dict.fromkeys(("flysim", "flyeye", "adapter"), fingerprint),
        **{f"{key}_sha256": fingerprint for key in ("graph", "annotations", "parameters", "calibration")},
    }
    catalog = {"fixture": False, "files": [
        {"filename": name, "sha256": fingerprint, "size_bytes": 12}
        for name in ("body-annotations.feather", "body-neurotransmitters.feather", "connectome-weights.feather")
    ]}
    manifest = {"source": catalog, "graph_sha256": fingerprint}
    files = {"build/flytrap-v1/manifest.json": manifest,
             "artifacts/milestones/05/trials/baseline.json": checkpoint,
             "flytrap/data/sources.json": catalog}
    for relative, payload in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload))
    monkeypatch.setattr(environment, "_identity", lambda _: {"status": "ok", "bytes": 12, "sha256": fingerprint})
    assert environment.inspect_model_identity(tmp_path)["status"] == "ok"
    checkpoint["model_source_sha256"]["adapter"] = "b" * 64
    (tmp_path / "artifacts/milestones/05/trials/baseline.json").write_text(json.dumps(checkpoint))
    report = environment.inspect_model_identity(tmp_path)
    assert report["status"] == "blocked"
    assert any("adapter source identity mismatch" in error for error in report["errors"])
    catalog["fixture"] = True
    (tmp_path / "flytrap/data/sources.json").write_text(json.dumps(catalog))
    report = environment.inspect_model_identity(tmp_path)
    assert any("pinned full real dataset" in error for error in report["errors"])


def test_cli_blocked_exit_and_non_overwriting_evidence(tmp_path, monkeypatch, capsys):
    from flytrap.live import __main__ as cli
    monkeypatch.setattr(cli, "discover_devices", lambda: {"status": "blocked", "capture_started": False})
    assert main(["devices", "--evidence-dir", str(tmp_path)]) == 2
    saved = (tmp_path / "devices.json").read_bytes()
    assert json.loads(saved)["capture_started"] is False
    with pytest.raises(SystemExit) as error:
        main(["devices", "--evidence-dir", str(tmp_path)])
    assert error.value.code == 2
    assert (tmp_path / "devices.json").read_bytes() == saved
    capsys.readouterr()


def test_serve_binds_only_loopback_without_doctor_or_discovery(monkeypatch):
    import uvicorn
    from flytrap.live import __main__ as cli
    calls = []
    monkeypatch.setattr(uvicorn, "run", lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setattr(cli, "discover_devices", lambda: pytest.fail("serve scanned devices"))
    monkeypatch.setattr(cli, "inspect_environment", lambda: pytest.fail("serve ran doctor"))
    assert main(["serve", "--port", "8888"]) == 0
    assert calls[0][1]["host"] == "127.0.0.1"
    assert calls[0][1]["port"] == 8888
    app = calls[0][0][0]
    assert app.state.service.execution_purpose == "automated"
    assert not app.state.service.sessions
    assert calls[0][1]["workers"] == 1


@pytest.mark.parametrize("arguments", [["serve", "--port", "80"], ["serve", "--port", "65536"],
                                       ["serve", "--host", "0.0.0.0"],
                                       ["devices", "--source", "https://camera.invalid"]])
def test_cli_rejects_privileged_ports_and_arbitrary_capture_configuration(arguments):
    with pytest.raises(SystemExit) as error:
        main(arguments)
    assert error.value.code == 2
