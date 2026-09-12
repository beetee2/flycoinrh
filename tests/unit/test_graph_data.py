"""Synthetic raw-connectome boundary regressions, never a real-model gate."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from flytrap.data.graph import anatomy_inputs, build_graph, graph_from_arrays


@pytest.fixture
def synthetic_tables():
    fixture = json.loads((Path(__file__).parents[1] / "fixtures/connectome.json").read_text())
    assert fixture["fixture"] is True
    tables = [pd.DataFrame(fixture[name]) for name in ("weights", "annotations", "neurotransmitters")]
    return fixture, tables


def test_hand_computed_incoming_anatomy_resists_reversed_lookup(synthetic_tables):
    fixture, tables = synthetic_tables
    graph = build_graph(*tables)
    expected = fixture["expected"]
    inputs = anatomy_inputs(graph)
    for name in ("mbon_bodies", "pam_counts", "ppl1_counts", "classification"):
        np.testing.assert_array_equal(inputs[name], expected[name])
    np.testing.assert_array_equal(graph.bodies, expected["bodies"])
    assert graph.anatomy.nnz == expected["anatomy_nnz"]
    assert graph.anatomy.sum() == expected["anatomy_synapses"]
    assert graph.anatomy.dtype == np.int64
    # Deliberately strong MBON -> PAM distractors yield [30, 40, 0, 0],
    # which cannot be mistaken for the hand-computed incoming [5, 3, 4, 0].
    np.testing.assert_array_equal(graph.anatomy[0, 2:6].toarray()[0], [30, 40, 0, 0])


def test_fast_weights_have_post_pre_orientation_and_presynaptic_sign(synthetic_tables):
    _, tables = synthetic_tables
    graph = build_graph(*tables)
    expected = np.zeros((8, 8), dtype=np.float32)
    expected[0, 2] = 8.25  # 200 -> 7: 30 acetylcholine synapses
    expected[0, 3] = -11.0  # 300 -> 7: 40 GABA synapses
    expected[2, 6] = 1.1  # 900 -> 200: 4 acetylcholine synapses
    expected[2, 3] = -0.825  # 300 -> 200: 3 GABA synapses
    np.testing.assert_allclose(graph.W.toarray(), expected, rtol=1e-6)
    assert graph.W.nnz == 4


def test_transposing_fast_matrix_cannot_recover_dopamine_inputs(synthetic_tables):
    _, tables = synthetic_tables
    graph = build_graph(*tables)
    assert graph.anatomy[2, 0] == 5
    assert graph.anatomy[2, 1] == 3
    assert graph.W[:, :2].nnz == 0  # every dopamine output was removed
    assert graph.W.T[:2, :].nnz == 0  # transposition does not restore counts
    assert graph.W[0, 2] == pytest.approx(8.25)  # reversed lookup sees the distractor


def test_duplicates_are_aggregated_before_threshold_and_zero_removed(synthetic_tables):
    _, tables = synthetic_tables
    graph = build_graph(*tables)
    assert graph.anatomy[2, 0] == 5  # 2 + 3, not only the individually retained 3
    assert graph.anatomy[5, 6] == 0  # 1 + 1 stays below the threshold of 3
    assert graph.anatomy[4, 6] == 0  # explicit zero never becomes a stored edge
    assert np.all(graph.anatomy.data >= 3)
    assert graph.anatomy.has_canonical_format


def test_body_order_and_metadata_preserve_sparse_large_ids_and_missing_values(synthetic_tables):
    _, tables = synthetic_tables
    graph = build_graph(*tables)
    assert graph.W.shape == (8, 8)  # allocation follows neuron count, not maximum body ID
    assert int(graph.bodies[-1]) == 9007199254740993
    assert graph.bodies.dtype == np.int64
    np.testing.assert_array_equal(graph.metadata["types"],
                                  ["PAM01", "PPL101", "MBON01", "MBON02", "MBON03", "MBON04", "KC", ""])
    np.testing.assert_array_equal(graph.metadata["sign"], [0, 0, 1, -1, 0, 0, 1, 0])
    assert graph.metadata["nt"][3] == "gaba"
    assert graph.metadata["nt"][4] == "unrecognized_synthetic_nt"
    assert graph.metadata["nt"][5] == "unknown"
    for field, value in (("superclass", "central"), ("subclass", "intrinsic"),
                         ("receptor", "synthetic_receptor"), ("fru", "synthetic_fru")):
        assert graph.metadata[field][6] == value
        assert graph.metadata[field][7] == ""
    assert graph.anatomy[2, 7] == 6
    assert graph.W[2, 7] == 0


def test_array_round_trip_preserves_anatomy_and_upstream_fields(synthetic_tables, tmp_path):
    _, tables = synthetic_tables
    graph = build_graph(*tables)
    path = tmp_path / "synthetic-graph.npz"
    np.savez_compressed(path, **graph.arrays())
    with np.load(path, allow_pickle=False) as archive:
        restored = graph_from_arrays(dict(archive), min_syn=3)
    assert restored.min_syn == 3
    for name, value in graph.arrays().items():
        np.testing.assert_array_equal(restored.arrays()[name], value)
    for name, value in anatomy_inputs(graph).items():
        np.testing.assert_array_equal(anatomy_inputs(restored)[name], value)


@pytest.mark.parametrize("value", [-1, 1.5, float("nan"), float("inf"), "bad", True])
def test_invalid_synapse_counts_fail_clearly(synthetic_tables, value):
    _, tables = synthetic_tables
    tables[0]["weight"] = tables[0]["weight"].astype(object)
    tables[0].loc[0, "weight"] = value
    with pytest.raises(ValueError):
        build_graph(*tables)


@pytest.mark.parametrize("value", [-1, 1.25, float("nan"), "bad", True, 2**63])
def test_invalid_body_ids_fail_clearly(synthetic_tables, value):
    _, tables = synthetic_tables
    tables[0]["body_pre"] = tables[0]["body_pre"].astype(object)
    tables[0].loc[0, "body_pre"] = value
    with pytest.raises(ValueError):
        build_graph(*tables)


@pytest.mark.parametrize("table,column", [(0, "body_post"), (0, "weight"), (1, "bodyId"),
                                           (1, "status"), (2, "consensus_nt")])
def test_missing_required_columns_are_errors(synthetic_tables, table, column):
    _, tables = synthetic_tables
    tables[table] = tables[table].drop(columns=[column])
    with pytest.raises(ValueError):
        build_graph(*tables)


@pytest.mark.parametrize("threshold", [0, -1, 1.5, True])
def test_invalid_threshold_rejected(synthetic_tables, threshold):
    _, tables = synthetic_tables
    with pytest.raises(ValueError):
        build_graph(*tables, min_syn=threshold)


def test_entirely_unmapped_edges_do_not_create_plausible_empty_model(synthetic_tables):
    _, tables = synthetic_tables
    tables[0] = pd.DataFrame([{"body_pre": 999, "body_post": 888, "weight": 10}])
    with pytest.raises(ValueError):
        build_graph(*tables)


@pytest.mark.parametrize("table,column,value", [(1, "type", "conflicting_type"),
                                                  (2, "consensus_nt", "gaba")])
def test_conflicting_duplicate_metadata_rejected(synthetic_tables, table, column, value):
    _, tables = synthetic_tables
    conflict = tables[table].iloc[[0]].copy()
    conflict[column] = value
    tables[table] = pd.concat([tables[table], conflict], ignore_index=True)
    with pytest.raises(ValueError):
        build_graph(*tables)


def test_consistent_duplicate_metadata_preserves_graph(synthetic_tables):
    _, tables = synthetic_tables
    expected = build_graph(*tables)
    for index in (1, 2):
        tables[index] = pd.concat([tables[index], tables[index].iloc[[0]]], ignore_index=True)
    actual = build_graph(*tables)
    for key, value in expected.arrays().items():
        np.testing.assert_array_equal(actual.arrays()[key], value)


def test_optional_annotation_columns_can_all_be_absent(synthetic_tables):
    _, tables = synthetic_tables
    tables[1] = tables[1][["bodyId", "status", "statusLabel"]]
    graph = build_graph(*tables)
    for field in ("types", "superclass", "subclass", "receptor", "fru"):
        assert graph.metadata[field].tolist() == [""] * 8
    inputs = anatomy_inputs(graph)
    for values in inputs.values():
        assert len(values) == 0


def test_synapse_aggregation_overflow_rejected(synthetic_tables):
    _, tables = synthetic_tables
    tables[0] = pd.DataFrame({"body_pre": [900, 900], "body_post": [200, 200],
                              "weight": [2**63 - 1, 1]})
    with pytest.raises(ValueError):
        build_graph(*tables)
