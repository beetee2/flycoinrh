"""Generated synthetic checks for connectome aggregation and stable indexing."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from hypothesis import given, settings, strategies as st

from flytrap.data.graph import anatomy_inputs, build_graph


@given(st.lists(st.integers(min_value=0, max_value=50), min_size=1, max_size=20),
       st.integers(min_value=1, max_value=20))
def test_duplicate_count_conservation_across_threshold(counts, threshold):
    # A separate qualifying edge keeps the graph valid when the generated pair is dropped.
    annotations = pd.DataFrame({"bodyId": [10, 20, 30], "status": ["Traced"] * 3,
                                "statusLabel": ["Neuron"] * 3, "type": ["PAM01", "MBON01", "KC"]})
    nts = pd.DataFrame({"body": [10, 20, 30], "consensus_nt": ["dopamine", "gaba", "acetylcholine"]})
    weights = pd.DataFrame({"body_pre": [10] * len(counts) + [30],
                           "body_post": [20] * (len(counts) + 1), "weight": counts + [threshold]})
    graph = build_graph(weights, annotations, nts, min_syn=threshold)
    total = sum(counts)
    retained = total if total >= threshold else 0
    assert graph.anatomy[1, 0] == retained
    assert graph.anatomy[1, 2] == threshold
    assert graph.anatomy.sum() == retained + threshold
    assert graph.W[1, 0] == 0
    assert graph.W[1, 2] > 0
    assert anatomy_inputs(graph)["pam_counts"][0] == retained


@settings(max_examples=30)
@given(st.integers(min_value=0, max_value=2**32 - 1))
def test_row_permutation_preserves_every_exported_array(seed):
    fixture = json.loads((Path(__file__).parents[1] / "fixtures/connectome.json").read_text())
    assert fixture["fixture"] is True
    tables = [pd.DataFrame(fixture[name]) for name in ("weights", "annotations", "neurotransmitters")]
    graph = build_graph(*tables)
    shuffled = build_graph(*(table.sample(frac=1, random_state=seed).reset_index(drop=True)
                             for table in tables))
    for key, value in graph.arrays().items():
        np.testing.assert_array_equal(shuffled.arrays()[key], value)
    assert shuffled.stats == graph.stats


@given(st.integers(min_value=2**53 + 1, max_value=2**63 - 3))
def test_adjacent_large_integer_ids_remain_distinct(first):
    annotations = pd.DataFrame({"bodyId": [first + 1, first], "status": ["Traced"] * 2,
                                "statusLabel": ["Neuron"] * 2, "type": ["MBON01", "PAM01"]})
    nts = pd.DataFrame({"body": [first, first + 1], "consensus_nt": ["dopamine", "acetylcholine"]})
    weights = pd.DataFrame({"body_pre": [first], "body_post": [first + 1], "weight": [7]})
    graph = build_graph(weights, annotations, nts)
    np.testing.assert_array_equal(graph.bodies, [first, first + 1])
    assert graph.anatomy.shape == (2, 2)
    assert graph.anatomy[1, 0] == 7
    assert graph.anatomy[0, 1] == 0
    assert anatomy_inputs(graph)["pam_counts"].tolist() == [7]
