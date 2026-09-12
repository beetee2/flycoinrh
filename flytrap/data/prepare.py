"""Operator-only preparation from pinned public MaleCNS objects."""
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import urllib.request

from .bundle import DataError, DatasetSource, file_sha256, load_bundle, write_bundle


def public_source() -> DatasetSource:
    return DatasetSource.model_validate_json(Path(__file__).with_name("sources.json").read_text())


def verify_raw(root: Path, source: DatasetSource) -> dict:
    """Validate every byte against the catalog before reading any Feather table."""
    checks = {}
    for entry in source.files:
        path = Path(root) / entry.filename
        if not path.is_file():
            raise DataError(f"missing raw data: {path}; run data-fetch or supply the pinned files")
        if path.stat().st_size != entry.size_bytes or file_sha256(path) != entry.sha256:
            raise DataError(f"raw data checksum/size mismatch: {path}")
        checks[entry.filename] = entry.sha256
    return checks


def fetch_data(root: Path) -> dict:
    """Download only catalog URLs to a new root, with generation and byte hashes pinned."""
    source = public_source()
    root = Path(root).resolve()
    if root.exists():
        verify_raw(root, source)
        return {"status": "PASS", "source": source.model_dump(), "raw_root": str(root), "reused": True}
    root.parent.mkdir(parents=True, exist_ok=True)
    needed = sum(entry.size_bytes for entry in source.files)
    if shutil.disk_usage(root.parent).free < needed + 512 * 1024**2:
        raise DataError("insufficient disk space for pinned raw data")
    stage = Path(tempfile.mkdtemp(prefix=".connectome-", dir=root.parent))
    try:
        for entry in source.files:
            if not entry.url.startswith("https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/"):
                raise DataError("source catalog URL outside approved public dataset")
            url = entry.url + "?generation=" + entry.generation
            md5 = hashlib.md5(usedforsecurity=False)
            size = 0
            with urllib.request.urlopen(url, timeout=60) as response, (stage / entry.filename).open("xb") as stream:
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > entry.size_bytes:
                        raise DataError(f"download exceeds pinned size: {entry.filename}")
                    md5.update(chunk)
                    stream.write(chunk)
                stream.flush()
                os.fsync(stream.fileno())
            if size != entry.size_bytes or base64.b64encode(md5.digest()).decode() != entry.md5_base64:
                raise DataError(f"download size/MD5 mismatch: {entry.filename}")
        verify_raw(stage, source)
        (stage / "source.json").write_text(source.model_dump_json(indent=2) + "\n")
        if root.exists():
            raise DataError(f"raw output appeared during acquisition: {root}")
        stage.rename(root)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return {"status": "PASS", "source": source.model_dump(), "raw_root": str(root), "reused": False}


def build_data(raw_root: Path, graph_root: Path, *, min_syn: int = 3) -> dict:
    import pandas as pd
    from .graph import build_graph, selected_bodies

    source = public_source()
    verify_raw(raw_root, source)
    annotations = pd.read_feather(raw_root / "body-annotations.feather")
    weights, raw_rows = read_mapped_weights(raw_root / "connectome-weights.feather", selected_bodies(annotations))
    graph = build_graph(
        weights, annotations,
        pd.read_feather(raw_root / "body-neurotransmitters.feather", columns=["body", "consensus_nt"]),
        min_syn=min_syn,
    )
    graph.stats["raw_edge_rows"] = raw_rows
    graph.stats["excluded_endpoint_rows"] += raw_rows - len(weights)
    manifest = write_bundle(graph, graph_root, source)
    return {"status": "PASS", "fixture": source.fixture, "graph_root": str(graph_root.resolve()),
            "preparation_stats": graph.stats, "manifest": manifest.model_dump()}


def read_mapped_weights(path: Path, bodies) -> tuple:
    """Read Arrow IPC/Feather v2 batches; never discard subthreshold duplicates."""
    import numpy as np
    import pandas as pd
    import pyarrow as pa
    import pyarrow.compute as pc
    from .graph import validate_weights

    parts = []
    total = 0
    value_set = pa.array(bodies)
    with pa.memory_map(str(path), "r") as stream:
        reader = pa.ipc.open_file(stream)
        names = ["body_pre", "body_post", "weight"]
        if not set(names) <= set(reader.schema.names):
            raise DataError("weight file missing body_pre/body_post/weight columns")
        for number in range(reader.num_record_batches):
            batch = reader.get_batch(number).select(names)
            # Validate malformed rows even if an endpoint will be excluded.
            validate_weights(batch.to_pandas())
            total += batch.num_rows
            mapped = pc.and_(pc.is_in(batch.column("body_pre"), value_set=value_set),
                             pc.is_in(batch.column("body_post"), value_set=value_set))
            kept = batch.filter(mapped)
            if kept.num_rows:
                parts.append(tuple(kept.column(name).to_numpy().astype(np.int64) for name in names))
    if not parts:
        raise DataError("no raw edges connect eligible Traced bodies")
    return pd.DataFrame({name: np.concatenate([part[index] for part in parts])
                         for index, name in enumerate(names)}), total


def data_doctor(raw_root: Path, graph_root: Path, *, allow_fixture: bool = False) -> dict:
    source = public_source()
    raw_hashes = verify_raw(raw_root, source)
    graph, manifest = load_bundle(graph_root, allow_fixture=allow_fixture)
    if manifest.source != source:
        raise DataError("graph source does not match the pinned public source catalog")
    return {"status": "PASS", "fixture": False, "raw_hashes": raw_hashes,
            "graph_root": str(graph_root.resolve()), "graph_sha256": manifest.graph_sha256,
            "stats": graph.stats, "learning_enabled": False, "real_model_available": False,
            "note": "Data gate only; controller integration and behavior are separate milestones."}


def run_command(command: str, raw_root: Path, graph_root: Path, min_syn: int) -> int:
    try:
        if command == "data-fetch":
            result = fetch_data(raw_root)
        elif command == "data-build":
            result = build_data(raw_root, graph_root, min_syn=min_syn)
        else:
            result = data_doctor(raw_root, graph_root)
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc), "learning_enabled": False}))
        return 1
