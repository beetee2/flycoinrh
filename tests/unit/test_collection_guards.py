from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.parametrize("kind", ["empty", "all_skipped"])
def test_unexecuted_suite_cannot_exit_success(tmp_path, kind):
    if kind == "all_skipped":
        source = Path(__file__).resolve().parents[1] / "conftest.py"
        (tmp_path / "conftest.py").write_text(source.read_text())
        (tmp_path / "test_skipped.py").write_text(
            'import pytest\n@pytest.mark.skip(reason="guard probe")\ndef test_never_run():\n    assert False\n'
        )
    result = subprocess.run([sys.executable, "-m", "pytest", "-q", str(tmp_path)],
                            cwd=tmp_path, text=True, capture_output=True, timeout=10)
    assert result.returncode == 5, result.stdout + result.stderr
