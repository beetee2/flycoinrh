"""Checksummed, explicit graph bundles. Loading never enables learning."""
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import tempfile
from typing import Literal
import zipfile
import zlib

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

from .graph import GraphData, anatomy_inputs, graph_from_arrays


class DataError(ValueError):
    """Invalid or unavailable data, never a request to substitute fixtures."""


class SourceFile(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    filename: str = Field(pattern=r"^[a-z-]+\.feather$")
    url: str
    generation: str
    size_bytes: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    md5_base64: str


class DatasetSource(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    dataset: str
    version: str
    fixture: bool
    attribution: str
    license: str
    reference_url: str
    files: list[SourceFile] = Field(min_length=3, max_length=3)


class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    schema_version: Literal["flytrap-graph-1"] = "flytrap-graph-1"
    created_utc: str
    source: DatasetSource
    builder: dict[str, str | None]
    environment: dict[str, str]
    policy: dict[str, str | int | float]
    hashes: dict[str, str]
    stats: dict[str, int]
    graph_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    learning_enabled: Literal[False] = False


def file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def array_hash(array: np.ndarray) -> str:
    """Hash logical arrays, independent of native integer widths/endianness."""
    if array.dtype.kind in "US":
        payload = json.dumps(array.tolist(), ensure_ascii=False, separators=(",", ":")).encode()
        kind = "text"
    elif array.dtype.kind in "iu":
        payload, kind = array.astype("<i8").tobytes(), "int64"
    elif array.dtype.kind == "f":
        payload, kind = array.astype("<f4").tobytes(), "float32"
    else:
        raise DataError("unsupported graph array dtype")
    header = json.dumps([kind, list(array.shape)], separators=(",", ":")).encode()
    return hashlib.sha256(header + b"\n" + payload).hexdigest()


def graph_hashes(graph: GraphData) -> dict[str, str]:
    arrays = graph.arrays()
    hashes = {name: array_hash(np.asarray(value)) for name, value in arrays.items()}
    hashes.update({"input_" + name: array_hash(value) for name, value in anatomy_inputs(graph).items()})
    return hashes


def policy(min_syn: int) -> dict:
    return {
        "orientation": "post,pre", "min_syn": min_syn, "mv_per_synapse": 0.275,
        "threshold": "sum duplicate directed pairs, then keep count >= min_syn",
        "neurons": "status == Traced and statusLabel != Glia; both endpoints mapped",
        "anatomy": "unsigned counts before neurotransmitter signs, same threshold as fast matrix",
        "classification": "type-prefix PAM/PPL1 inputs to type-prefix MBON; ties/zeros explicit; heuristic only",
    }


def builder_identity() -> dict:
    root = Path(__file__).resolve().parents[2]
    files = {str(path.relative_to(root)): file_sha256(path)
             for path in sorted(Path(__file__).parent.glob("*.py"))}
    result = {"package_version": importlib.metadata.version("flytrap"),
              "data_code_sha256": hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest(),
              "upstream_revision": "8748e5bd30794d14afeb3441904221b52a002cac", "source_commit": None}
    if (root / ".git").exists():
        result["source_commit"] = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "HEAD"], text=True, timeout=5).strip()
    return result


def write_bundle(graph: GraphData, output: Path, source: DatasetSource) -> Manifest:
    """Publish a new directory; never overwrite an existing graph or checkpoint."""
    output = Path(output).resolve()
    if output.exists():
        raise DataError(f"graph output already exists: {output}")
    # Validate even caller-created GraphData before publication.
    checked = graph_from_arrays(graph.arrays(), min_syn=graph.min_syn)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".graph-", dir=output.parent))
    try:
        graph_path = stage / "graph.npz"
        np.savez_compressed(graph_path, **checked.arrays())
        manifest = Manifest(
            created_utc=datetime.now(timezone.utc).isoformat(), source=source,
            builder=builder_identity(),
            environment={"python": platform.python_version(), **{
                name: importlib.metadata.version(name) for name in ("numpy", "scipy", "pandas", "pyarrow")}},
            policy=policy(graph.min_syn), hashes=graph_hashes(checked), stats=checked.stats,
            graph_sha256=file_sha256(graph_path),
        )
        (stage / "manifest.json").write_text(manifest.model_dump_json(indent=2) + "\n")
        for name in ("graph.npz", "manifest.json"):
            with (stage / name).open("rb") as stream:
                os.fsync(stream.fileno())
        # POSIX rename refuses an occupied nonempty output directory.
        if output.exists():
            raise DataError(f"graph output already exists: {output}")
        stage.rename(output)
        fd = os.open(output.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        return manifest
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def load_bundle(root: Path, *, allow_fixture: bool = False) -> tuple[GraphData, Manifest]:
    root = Path(root).resolve()
    try:
        manifest = Manifest.model_validate_json((root / "manifest.json").read_text())
        if manifest.source.fixture and not allow_fixture:
            raise DataError("fixture graph is forbidden for a real-data gate")
        if manifest.graph_sha256 != file_sha256(root / "graph.npz"):
            raise DataError("graph checksum mismatch")
        minimum = manifest.policy.get("min_syn")
        if type(minimum) is not int or manifest.policy != policy(minimum):
            raise DataError("unsupported graph policy")
        with np.load(root / "graph.npz", allow_pickle=False) as archive:
            graph = graph_from_arrays(dict(archive), min_syn=minimum)
        if graph_hashes(graph) != manifest.hashes:
            raise DataError("graph mapping/metadata checksum mismatch")
        if graph.stats != manifest.stats:
            raise DataError("graph statistics mismatch")
        return graph, manifest
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile, zlib.error) as exc:
        raise DataError(f"invalid graph bundle at {root}: {exc}") from exc
