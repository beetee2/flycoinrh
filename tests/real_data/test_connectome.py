"""Real MaleCNS data gate; missing files fail and fixtures cannot satisfy it."""

import json
import os
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.feather as feather
import pytest

from flytrap.data.bundle import load_bundle
from flytrap.data.prepare import data_doctor

pytestmark = pytest.mark.timeout(120)


@pytest.fixture(scope="module")
def real_bundle():
    raw_root = Path(os.environ.get("FLYTRAP_RAW_ROOT", "data"))
    graph_root = Path(os.environ.get("FLYTRAP_GRAPH_ROOT", "build/flytrap-v1"))
    required = [raw_root / name for name in (
        "body-annotations.feather", "body-neurotransmitters.feather", "connectome-weights.feather"
    )] + [graph_root / "graph.npz", graph_root / "manifest.json"]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        pytest.fail("Real-data gate requires the pinned raw files and graph bundle: " + ", ".join(missing))
    doctor = data_doctor(raw_root, graph_root)
    assert doctor["status"] == "PASS"
    assert doctor["fixture"] is False
    graph, manifest = load_bundle(graph_root)
    print(json.dumps({"gate": "real_data", "doctor": doctor}, sort_keys=True))
    return raw_root, graph_root, graph, manifest


def test_real_provenance_mapping_and_upstream_loader(real_bundle):
    raw_root, graph_root, graph, manifest = real_bundle
    assert manifest.source.fixture is False
    assert manifest.learning_enabled is False
    assert all(entry.sha256 and entry.generation for entry in manifest.source.files)
    annotation_path = raw_root / "body-annotations.feather"
    with pa.memory_map(str(annotation_path), "r") as source:
        names = pa.ipc.open_file(source).schema.names
    columns = ["bodyId", "status"]
    if "statusLabel" in names:
        columns.append("statusLabel")
    ann = feather.read_table(annotation_path, columns=columns).to_pandas()
    selected = ann["status"] == "Traced"
    if "statusLabel" in ann:
        selected &= ann["statusLabel"] != "Glia"
    expected = np.sort(ann.loc[selected, "bodyId"].unique())
    np.testing.assert_array_equal(graph.bodies, expected)
    assert np.all(graph.bodies[1:] > graph.bodies[:-1])
    assert graph.anatomy.nnz > graph.W.nnz > 0
    assert np.all(graph.anatomy.data >= graph.min_syn)
    assert np.any(graph.W.data > 0) and np.any(graph.W.data < 0)
    dopamine = np.flatnonzero(graph.metadata["nt"] == "dopamine")
    assert len(dopamine) > 0
    assert graph.anatomy[:, dopamine].nnz > 0
    assert graph.W[:, dopamine].nnz == 0

    from flysim import FlyBrain

    brain = FlyBrain(graph_path=graph_root / "graph.npz")
    assert brain.n == len(expected)
    np.testing.assert_array_equal(brain.bodies, expected)
    assert brain.W.shape == graph.W.shape
    assert brain.W.nnz == graph.W.nnz
    assert (brain.W - graph.W).nnz == 0
    print(json.dumps({"upstream_loader": "PASS", "bodies": brain.n,
                      "anatomical_edges": graph.anatomy.nnz, "fast_edges": graph.W.nnz,
                      "dopamine_bodies": len(dopamine), "simulation_executed": False}))


def test_raw_directed_counts_and_dopamine_mbon_anatomy(real_bundle):
    raw_root, _, graph, _ = real_bundle
    types = graph.metadata["types"]
    nt = graph.metadata["nt"]
    mbon = np.flatnonzero(np.char.startswith(types, "MBON"))
    dopamine = np.flatnonzero(nt == "dopamine")
    subgraph = graph.anatomy[mbon][:, dopamine].tocoo()
    assert subgraph.nnz > 0, "Real dopamine-to-MBON anatomical connections are required"
    strongest = int(np.argmax(subgraph.data))
    pairs = [(int(mbon[subgraph.row[strongest]]), int(dopamine[subgraph.col[strongest]]))]
    # Include independent positive and negative fast pathways from the real graph.
    for positive in (True, False):
        offset = int(np.flatnonzero((graph.W.data > 0) if positive else (graph.W.data < 0))[0])
        post = int(np.searchsorted(graph.W.indptr, offset, side="right") - 1)
        pairs.append((post, int(graph.W.indices[offset])))
    directed = set(pairs) | {(pre, post) for post, pre in pairs}
    totals = {(int(graph.bodies[pre]), int(graph.bodies[post])): 0 for post, pre in directed}
    selected_pre = np.asarray(sorted({pre for pre, _ in totals}), dtype=np.int64)
    selected_post = np.asarray(sorted({post for _, post in totals}), dtype=np.int64)
    with pa.memory_map(str(raw_root / "connectome-weights.feather"), "r") as source:
        reader = pa.ipc.open_file(source)
        rows_scanned = 0
        for index in range(reader.num_record_batches):
            batch = reader.get_batch(index)
            pre = batch.column("body_pre").to_numpy()
            post = batch.column("body_post").to_numpy()
            count = batch.column("weight").to_numpy()
            rows_scanned += len(pre)
            selected = np.flatnonzero(np.isin(pre, selected_pre) & np.isin(post, selected_post))
            for offset in selected:
                pair = (int(pre[offset]), int(post[offset]))
                if pair in totals:
                    totals[pair] += int(count[offset])
    raw_nt = feather.read_table(raw_root / "body-neurotransmitters.feather", columns=[
        "body", "consensus_nt"
    ]).to_pandas().set_index("body")["consensus_nt"]
    expected_signs = {"acetylcholine": 1, "gaba": -1, "glutamate": -1, "histamine": -1}
    details = []
    for post, pre in sorted(directed):
        pre_body, post_body = int(graph.bodies[pre]), int(graph.bodies[post])
        raw_count = totals[(pre_body, post_body)]
        retained = raw_count if raw_count >= graph.min_syn else 0
        assert int(graph.anatomy[post, pre]) == retained
        transmitter = raw_nt.get(pre_body)
        sign = expected_signs.get(transmitter, 0)
        expected_weight = np.float32(retained) * np.float32(0.275) * np.float32(sign)
        assert graph.W[post, pre] == pytest.approx(float(expected_weight), rel=1e-6, abs=1e-7)
        details.append({"body_pre": pre_body, "body_post": post_body,
                        "raw_synapses": raw_count, "anatomical_synapses": retained,
                        "fast_weight": float(graph.W[post, pre])})
    dopamine_post, dopamine_pre = pairs[0]
    assert raw_nt.loc[int(graph.bodies[dopamine_pre])] == "dopamine"
    raw_ann = feather.read_table(raw_root / "body-annotations.feather", columns=[
        "bodyId", "type", "flywireType", "instance"
    ]).to_pandas().set_index("bodyId")
    target_annotation = raw_ann.loc[int(graph.bodies[dopamine_post])]
    source_type = target_annotation[["type", "flywireType", "instance"]].dropna().iloc[0]
    assert source_type.startswith("MBON")
    assert graph.anatomy[dopamine_post, dopamine_pre] > 0
    assert graph.W[dopamine_post, dopamine_pre] == 0
    print(json.dumps({"raw_rows_scanned": rows_scanned, "orientation": "post,pre",
                      "checked_directed_pairs": details}, sort_keys=True))
