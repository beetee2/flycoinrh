import json
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix

from flysim import FlyBrain


def test_synthetic_graph_loads_and_repeats_windowed_simulation(tmp_path):
    fixture = json.loads((Path(__file__).resolve().parents[1] / "fixtures/tiny_graph.json").read_text())
    assert fixture["fixture"] is True
    rows, cols, values = zip(*fixture["edges"])
    weights = csr_matrix((values, (rows, cols)), shape=(3, 3), dtype=np.float32)
    path = tmp_path / "fixture-graph.npz"
    empty = np.array(["", "", ""])
    np.savez_compressed(path, data=weights.data, indices=weights.indices, indptr=weights.indptr,
        shape=weights.shape, bodies=fixture["bodies"], types=fixture["types"], nt=fixture["nt"],
        sign=fixture["sign"], superclass=empty, subclass=empty, receptor=empty, fru=empty)
    brain = FlyBrain(graph_path=path)
    assert brain.W[1, 0] == 8.25
    assert brain.W[0, 1] == 0
    first = brain.run({(0,): 5000.0}, steps=25, seed=13, spike_log=True)
    second = brain.run({(0,): 5000.0}, steps=25, seed=13, spike_log=True)
    assert first["_spikes_per_sec"] > 0
    assert 1 in first["_fired"]  # actual propagation through the synthetic edge
    assert first["_mean_mv"] == second["_mean_mv"]
    for a, b in zip(first["_spikes"], second["_spikes"], strict=True):
        np.testing.assert_array_equal(a, b)
