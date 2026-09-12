"""Graph persistence and controlled acquisition, using explicitly synthetic data."""
import base64
import hashlib
import io
import json
from pathlib import Path
import zipfile

import numpy as np
import pandas as pd
import pytest

from flytrap.data import prepare
from flytrap.data.bundle import (DataError, DatasetSource, array_hash, file_sha256,
                                 graph_hashes, load_bundle, write_bundle)
from flytrap.data.graph import build_graph


@pytest.fixture
def synthetic_source(tmp_path):
    fixture = json.loads((Path(__file__).parents[1] / "fixtures/connectome.json").read_text())
    assert fixture["fixture"]
    raw = tmp_path / "raw"
    raw.mkdir()
    files = []
    tables = []
    for key, name in [("weights", "connectome-weights.feather"),
                      ("annotations", "body-annotations.feather"),
                      ("neurotransmitters", "body-neurotransmitters.feather")]:
        table = pd.DataFrame(fixture[key])
        table.to_feather(raw / name)
        payload = (raw / name).read_bytes()
        files.append(dict(filename=name, url="https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/" + name,
                          generation="1", size_bytes=len(payload), sha256=file_sha256(raw / name),
                          md5_base64=base64.b64encode(hashlib.md5(payload, usedforsecurity=False).digest()).decode()))
        tables.append(table)
    source = DatasetSource(dataset="SYNTHETIC TEST ONLY", version="fixture-1", fixture=True,
                           attribution=fixture["provenance"], license="synthetic", reference_url="synthetic:test",
                           files=files)
    return source, raw, build_graph(*tables)


def test_bundle_roundtrip_and_fixture_gate(synthetic_source, tmp_path):
    source, _, graph = synthetic_source
    output = tmp_path / "graph"
    written = write_bundle(graph, output, source)
    restored, manifest = load_bundle(output, allow_fixture=True)
    assert manifest == written
    assert manifest.learning_enabled is False
    assert graph_hashes(restored) == graph_hashes(graph)
    with pytest.raises(DataError, match="fixture"):
        load_bundle(output)
    with pytest.raises(DataError, match="already exists"):
        write_bundle(graph, output, source)
    assert load_bundle(output, allow_fixture=True)[1] == written


@pytest.mark.parametrize("target", ["graph", "metadata", "statistics", "policy", "schema", "missing"])
def test_tampering_or_missing_bundle_is_rejected(synthetic_source, tmp_path, target):
    source, _, graph = synthetic_source
    output = tmp_path / "graph"
    write_bundle(graph, output, source)
    path = output / "manifest.json"
    manifest = json.loads(path.read_text())
    if target == "graph":
        with (output / "graph.npz").open("ab") as stream:
            stream.write(b"tampered")
    elif target == "metadata":
        manifest["hashes"]["bodies"] = "0" * 64
    elif target == "statistics":
        manifest["stats"]["invented"] = 123
    elif target == "policy":
        manifest["policy"]["orientation"] = "pre,post"
    elif target == "schema":
        manifest["schema_version"] = "unsupported"
    else:
        (output / "graph.npz").unlink()
    path.write_text(json.dumps(manifest))
    with pytest.raises(DataError):
        load_bundle(output, allow_fixture=True)


def test_no_pickle_loading_even_with_matching_file_digest(synthetic_source, tmp_path):
    source, _, graph = synthetic_source
    output = tmp_path / "graph"
    write_bundle(graph, output, source)
    arrays = graph.arrays()
    arrays["types"] = np.array([object()] * len(graph.bodies), dtype=object)
    np.savez_compressed(output / "graph.npz", **arrays)
    path = output / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["graph_sha256"] = file_sha256(output / "graph.npz")
    path.write_text(json.dumps(manifest))
    with pytest.raises(DataError, match="Object arrays"):
        load_bundle(output, allow_fixture=True)


def test_logical_hash_is_endian_independent_but_order_sensitive():
    assert array_hash(np.array([1, 2], dtype=">i8")) == array_hash(np.array([1, 2], dtype="<i4"))
    assert array_hash(np.array([1, 2])) != array_hash(np.array([2, 1]))


def test_raw_input_verification(synthetic_source):
    source, raw, _ = synthetic_source
    assert len(prepare.verify_raw(raw, source)) == 3
    (raw / source.files[0].filename).write_bytes(b"bad data")
    with pytest.raises(DataError, match="checksum/size mismatch"):
        prepare.verify_raw(raw, source)
    (raw / source.files[0].filename).unlink()
    with pytest.raises(DataError, match="missing raw data"):
        prepare.verify_raw(raw, source)


def test_controlled_fetch_checks_hashes_and_reuses_valid_files(synthetic_source, tmp_path, monkeypatch):
    source, raw, _ = synthetic_source
    calls = []
    monkeypatch.setattr(prepare, "public_source", lambda: source)
    def download(url, timeout):
        calls.append(url)
        assert timeout == 60
        assert url.endswith("?generation=1")
        return io.BytesIO((raw / url.split("/")[-1].split("?")[0]).read_bytes())
    monkeypatch.setattr(prepare.urllib.request, "urlopen", download)
    output = tmp_path / "fetched"
    assert prepare.fetch_data(output)["reused"] is False
    assert prepare.verify_raw(output, source)
    assert prepare.fetch_data(output)["reused"] is True
    assert len(calls) == 3


@pytest.mark.parametrize("failure", ["truncated", "oversize", "same_size_corruption", "network"])
def test_failed_fetch_publishes_nothing(synthetic_source, tmp_path, monkeypatch, failure):
    source, raw, _ = synthetic_source
    monkeypatch.setattr(prepare, "public_source", lambda: source)
    def download(url, timeout):
        payload = (raw / source.files[0].filename).read_bytes()
        if failure == "network":
            raise OSError("network unavailable")
        if failure == "truncated":
            payload = payload[:-1]
        elif failure == "oversize":
            payload += b"x"
        else:
            payload = b"x" * len(payload)
        return io.BytesIO(payload)
    monkeypatch.setattr(prepare.urllib.request, "urlopen", download)
    output = tmp_path / "fetched"
    with pytest.raises((DataError, OSError)):
        prepare.fetch_data(output)
    assert not output.exists()
    assert not list(tmp_path.glob(".connectome-*"))


def test_missing_data_command_is_nonzero_and_structured(tmp_path, capsys):
    from flytrap.cli import main
    assert main(["data-doctor", "--raw-root", str(tmp_path / "missing"),
                 "--graph-root", str(tmp_path / "graph")]) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "BLOCKED"
    assert result["learning_enabled"] is False


def test_corrupt_archive_surfaces_as_data_error(synthetic_source, tmp_path):
    source, _, graph = synthetic_source
    output = tmp_path / "graph"
    write_bundle(graph, output, source)
    with zipfile.ZipFile(output / "graph.npz", "w") as archive:
        archive.writestr("data.npy", b"malformed numpy")
    path = output / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["graph_sha256"] = file_sha256(output / "graph.npz")
    path.write_text(json.dumps(manifest))
    with pytest.raises(DataError):
        load_bundle(output, allow_fixture=True)


def test_streaming_build_keeps_duplicates_across_batches(synthetic_source, tmp_path, monkeypatch):
    import pyarrow as pa
    from flytrap.data.graph import selected_bodies

    source, raw, expected = synthetic_source
    path = raw / "connectome-weights.feather"
    frame = pd.read_feather(path)
    table = pa.Table.from_pandas(frame)
    with pa.OSFile(str(path), "wb") as stream, pa.ipc.new_file(stream, table.schema) as writer:
        writer.write_table(table, max_chunksize=1)
    weights, total = prepare.read_mapped_weights(path, selected_bodies(pd.read_feather(raw / "body-annotations.feather")))
    assert total == len(frame)
    assert len(weights) == len(frame) - 3
    record = next(item for item in source.files if item.filename == path.name)
    record.size_bytes = path.stat().st_size
    record.sha256 = file_sha256(path)
    monkeypatch.setattr(prepare, "public_source", lambda: source)
    result = prepare.build_data(raw, tmp_path / "graph")
    assert result["fixture"] is True
    restored, _ = load_bundle(tmp_path / "graph", allow_fixture=True)
    assert graph_hashes(restored) == graph_hashes(expected)
    assert result["preparation_stats"]["excluded_endpoint_rows"] == 3
    assert result["preparation_stats"]["raw_edge_rows"] == len(frame)


def test_streaming_validates_even_unmapped_rows(tmp_path):
    path = tmp_path / "invalid.feather"
    pd.DataFrame({"body_pre": [999], "body_post": [998], "weight": [-1]}).to_feather(path)
    with pytest.raises(ValueError, match="weight"):
        prepare.read_mapped_weights(path, np.array([1, 2], dtype=np.int64))


def test_broken_zip_with_matching_digest_is_a_structured_error(synthetic_source, tmp_path):
    source, _, graph = synthetic_source
    output = tmp_path / "graph"
    write_bundle(graph, output, source)
    (output / "graph.npz").write_bytes(b"PK\x03\x04broken zip")
    path = output / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["graph_sha256"] = file_sha256(output / "graph.npz")
    path.write_text(json.dumps(manifest))
    with pytest.raises(DataError, match="invalid graph bundle"):
        load_bundle(output, allow_fixture=True)
