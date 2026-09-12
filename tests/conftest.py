from pathlib import Path

import pytest

from flytrap.config import Settings


@pytest.fixture
def settings(tmp_path: Path):
    return Settings(profile="fixture", data_root=tmp_path / "data", artifact_root=tmp_path / "runs")


def pytest_collection_modifyitems(items):
    for item in items:
        parts = Path(str(item.path)).parts
        for section in ("unit", "property", "contracts", "db", "api", "worker"):
            if section in parts:
                item.add_marker(getattr(pytest.mark, "contract" if section == "contracts" else section))


def pytest_sessionfinish(session, exitstatus):
    # Pytest ordinarily handles zero collection; also reject an all-skipped suite.
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if exitstatus == 0 and reporter is not None and not reporter.stats.get("passed"):
        session.exitstatus = pytest.ExitCode.NO_TESTS_COLLECTED
