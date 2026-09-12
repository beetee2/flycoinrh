"""Operator configuration. No upstream .env file or wallet settings are read."""
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class Settings:
    profile: Literal["real", "fixture"] = "real"
    production: bool = False
    data_root: Path = Path("artifacts/local/data")
    artifact_root: Path = Path("artifacts/local/runs")

    def __post_init__(self):
        if self.profile not in {"real", "fixture"}:
            raise ValueError("profile must be real or fixture")
        if self.production and self.profile == "fixture":
            raise ValueError("fixture profile is forbidden in production")
        for field in ("data_root", "artifact_root"):
            object.__setattr__(self, field, Path(getattr(self, field)).resolve())
        if self.data_root == self.artifact_root:
            raise ValueError("data and artifact roots must differ")

    @property
    def database_path(self) -> Path:
        return self.data_root / "flytrap.sqlite3"
