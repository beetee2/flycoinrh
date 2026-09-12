import json
from pathlib import Path
import subprocess
import sys

import pytest
from pydantic import ValidationError

from flytrap.cli import doctor
from flytrap.config import Settings
from flytrap.contracts import Observation
from flytrap.controllers.fixture import FixtureController, fixture_checkpoint
from flytrap.persistence import require_sqlite


def test_fixture_controller_has_no_neural_claim_and_resets():
    controller = FixtureController()
    dark = Observation(schema_version="1", pixels=[0.0] * 256)
    with pytest.raises(RuntimeError, match="reset"):
        controller.step(dark)
    controller.reset(run_seed=123, checkpoint=fixture_checkpoint())
    first = controller.step(dark)
    controller.reset(run_seed=123, checkpoint=fixture_checkpoint())
    assert controller.step(dark) == first
    assert first.model_mode == "fixture"
    assert first.telemetry.spike_count == 0
    assert first.telemetry.neural_ms == 0
    controller.reset(run_seed=123, checkpoint=fixture_checkpoint())
    assert controller.step(Observation(schema_version="1", pixels=[1.0] * 256)).dy != first.dy


@pytest.mark.parametrize("seed", [-1, 2**32, True, 1.5])
def test_fixture_rejects_invalid_seeds(seed):
    with pytest.raises(ValueError):
        FixtureController().reset(run_seed=seed, checkpoint=fixture_checkpoint())


def test_checkpoint_requires_exact_fixture_identity():
    changed = fixture_checkpoint().model_copy(update={"sha256": "0" * 64})
    with pytest.raises(ValueError, match="checkpoint"):
        FixtureController().reset(run_seed=0, checkpoint=changed)


def test_fixture_forbidden_in_production_and_default_is_real():
    assert Settings().profile == "real"
    with pytest.raises(ValueError, match="forbidden"):
        Settings(profile="fixture", production=True)
    with pytest.raises(ValueError, match="profile"):
        Settings(profile="other")


def test_sqlite_rejection_is_explicit():
    with pytest.raises(RuntimeError, match="rejected"):
        require_sqlite((3, 51, 2))
    require_sqlite((3, 51, 3))


def test_doctor_fixture_and_real_are_distinct(settings):
    assert doctor(settings)["status"] == "PASS"
    report = doctor(Settings(data_root=settings.data_root, artifact_root=settings.artifact_root))
    assert report["status"] == "BLOCKED"
    assert report["real_model_available"] is False
    assert report["checks"]["real_model_integration"] is False


def test_imports_have_no_upstream_services_or_filesystem_effects(tmp_path):
    code = """
import json, pathlib, sys
import flytrap.api, flytrap.worker, flytrap.cli
print(json.dumps({'files': list(str(p) for p in pathlib.Path('.').iterdir()),
 'forbidden': sorted(set(sys.modules) & {'roam', 'rhlive', 'rhwallet', 'rhprovider', 'voice', 'xpost', 'envcfg'})}))
"""
    result = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, text=True, capture_output=True, timeout=5)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"files": [], "forbidden": []}


def test_observation_cannot_carry_goal_information():
    with pytest.raises(ValidationError):
        Observation(schema_version="1", pixels=[0.0] * 256, target_x=1)


def test_controller_imports_only_declared_inputs():
    import ast
    directory = Path(__file__).resolve().parents[2] / "flytrap/controllers"
    # Graph metadata is explicit model state; the adapter cannot import task state.
    allowed = {"hashlib", "json", "pathlib", "typing", "numpy", "pandas", "pydantic",
               "random", "flyeye", "flysim", "flytrap.contracts", "flytrap.data.bundle"}
    for path in directory.glob("*.py"):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert node.level == 0 and node.module in allowed, path
                if node.module == "flytrap.contracts":
                    assert {name.name for name in node.names} <= {"CheckpointRef", "ControllerOutput", "Observation"}
                elif node.module == "flytrap.data.bundle":
                    assert {name.name for name in node.names} <= {"DatasetSource", "file_sha256", "load_bundle"}
            elif isinstance(node, ast.Import):
                assert {name.name for name in node.names} <= allowed, path
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {"__import__", "eval", "exec"}, path
