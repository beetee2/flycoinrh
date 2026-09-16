"""Dedicated CUDA gate over labeled synthetic graphs; never loads the connectome.

Adapted selectively from fruitflydev/flycoinrh test_flysim_gpu.py at
f2fdedf49bbd2712834c5404c690670af26c2028 (exact-reference, duplicate-drive,
refractory, output-type and repeatability checks). LICENSE and NOTICE apply.
The CPU implementation in this checkout is the numerical reference. CUDA is
required here: ordinary CPU CI must explicitly exclude tests/gpu.
"""
from pathlib import Path

import numpy as np
import pytest
import scipy.sparse as sp

from flysim import FlyBrain, Params


@pytest.fixture(scope="module")
def cuda():
    try:
        import torch
    except ImportError as error:
        pytest.fail(f"Dedicated GPU validation requires the pinned CUDA PyTorch extra: {error}")
    assert torch.cuda.is_available(), "Dedicated GPU validation requires an available CUDA device"
    assert torch.cuda.device_count() > 0, "Dedicated GPU validation requires CUDA device 0"
    return torch


def synthetic_graph(path: Path, edges=()):
    """Eight synthetic neurons; edges are (post, pre, exact float32 weight)."""
    n = 8
    post, pre, weight = zip(*edges) if edges else ([], [], [])
    matrix = sp.csr_matrix((np.asarray(weight, dtype=np.float32), (post, pre)), shape=(n, n))
    blank = np.full(n, "", dtype=str)
    np.savez(path, data=matrix.data, indices=matrix.indices, indptr=matrix.indptr,
             shape=np.asarray(matrix.shape), bodies=np.arange(n, dtype=np.int64),
             types=np.asarray([f"SYNTHETIC-{i % 2}" for i in range(n)]),
             superclass=blank, subclass=blank, receptor=blank, fru=blank, nt=blank)
    return path


def pair(tmp_path, cuda, *, edges=(), parameters=None):
    from flytrap.live.gpu import GPUInference

    brain = FlyBrain(synthetic_graph(tmp_path / "synthetic-graph.npz", edges), p=parameters or Params())
    return brain, GPUInference(brain, device="cuda:0")


def assert_contract_and_exact(reference, actual):
    assert set(actual) == set(reference)
    for key in reference:
        expected, received = reference[key], actual[key]
        assert type(received) is type(expected), key
        if key == "_spikes":
            assert len(received) == len(expected)
            for step, (a, b) in enumerate(zip(expected, received, strict=True)):
                assert b.dtype == a.dtype == np.dtype(np.int32)
                np.testing.assert_array_equal(a, b, err_msg=f"spikes at step {step}")
        elif isinstance(expected, np.ndarray):
            assert received.dtype == expected.dtype, key
            np.testing.assert_array_equal(expected, received, err_msg=key)
        else:
            assert received == expected, key
    assert type(actual["_total_spikes"]) is int
    assert actual["_fired"].dtype == np.dtype(np.int64)
    for key in ("_total_hz", "_spikes_per_sec", "_mean_mv"):
        assert type(actual[key]) is float


def compare(cpu, gpu, drive, *, steps=100, record=None, seed=17):
    gains = np.ones(cpu.n_types, dtype=np.float32)
    kwargs = dict(steps=steps, gains=gains, record=record, seed=seed, spike_log=True)
    reference = cpu.run(drive, **kwargs)
    actual = gpu.run(drive, **kwargs)
    assert_contract_and_exact(reference, actual)
    return actual


def test_no_drive_and_negative_edges_are_quiet(tmp_path, cuda):
    cpu, gpu = pair(tmp_path, cuda, edges=[(1, 0, -8), (0, 1, 8)])
    result = compare(cpu, gpu, {}, record={"all": np.arange(8), "empty": np.array([], dtype=np.int64)})
    assert result["_total_spikes"] == 0
    assert result["_mean_mv"] == -52.0
    assert result["_fired"].size == 0
    assert result["all"].dtype == np.float64
    assert all(spikes.size == 0 for spikes in result["_spikes"])


def test_reset_precedes_propagation_and_synapses_fire_next_step(tmp_path, cuda):
    class WithoutRefractory(Params):
        refractory = 0.0

    cpu, gpu = pair(tmp_path, cuda, parameters=WithoutRefractory(),
                    edges=[(0, 0, 8), (1, 0, 8), (2, 0, -8), (3, 1, 8)])
    first = compare(cpu, gpu, {(0,): 9000.0}, steps=1, record={"all": np.arange(8)})
    np.testing.assert_array_equal(first["_spikes"][0], [0])
    assert first["_mean_mv"] == -51.0  # reset -52, then +8,+8,-8 across eight cells
    result = compare(cpu, gpu, {(0,): 9000.0}, steps=3, record={"all": np.arange(8)})
    assert [entry.tolist() for entry in result["_spikes"]] == [[0], [0, 1], [0, 1, 3]]
    assert 2 not in result["_fired"]  # The negative edge cannot excite its target.


def test_leak_precedes_threshold_after_previous_synaptic_input(tmp_path, cuda):
    # A +7 input places neuron 1 exactly at threshold after step zero. The
    # following leak lowers it below threshold before the firing test.
    cpu, gpu = pair(tmp_path, cuda, edges=[(1, 0, 7)])
    result = compare(cpu, gpu, {(0,): 9000.0}, steps=3, record={"all": np.arange(8)})
    assert [entry.tolist() for entry in result["_spikes"]] == [[0], [], []]


def test_external_kick_is_overridden_by_refractory_reset(tmp_path, cuda):
    cpu, gpu = pair(tmp_path, cuda)
    result = compare(cpu, gpu, {(0,): 9000.0}, record={"driven": np.asarray([0])})
    fired_steps = [step for step, spikes in enumerate(result["_spikes"]) if len(spikes)]
    assert fired_steps == list(range(0, 100, 11))
    assert result["_total_spikes"] == 10
    np.testing.assert_array_equal(result["driven"], [500.0])


def test_threshold_equality_fires_after_exact_half_decay(tmp_path, cuda):
    class HalfDecay(Params):
        tau_m = Params.dt / np.log(2)

    cpu, gpu = pair(tmp_path, cuda, parameters=HalfDecay(), edges=[(1, 0, 14)])
    assert cpu.decay == np.float32(0.5)
    result = compare(cpu, gpu, {(0,): 9000.0}, steps=2, record={"all": np.arange(8)})
    assert [entry.tolist() for entry in result["_spikes"]] == [[0], [1]]


def test_duplicate_drive_uses_any_hit_and_preserves_numpy_random_stream(tmp_path, cuda):
    cpu, gpu = pair(tmp_path, cuda, edges=[(4, 0, 8), (5, 1, -8), (6, 2, 4), (6, 3, 4)])
    drive = {(0, 1, 2): np.asarray([180., 90., 400.], dtype=np.float32),
             (2, 3): np.asarray([250., 180.], dtype=np.float32)}
    result = compare(cpu, gpu, drive, record={"selected": np.asarray([6, 2, 2, 0]), "all": np.arange(8)},
                     seed=43)
    assert result["_total_spikes"] > 0
    assert result["selected"][1] == result["selected"][2]


def test_gpu_is_exactly_repeatable_and_resets_each_window(tmp_path, cuda):
    cpu, gpu = pair(tmp_path, cuda, edges=[(1, 0, 8), (2, 1, 8), (0, 2, -4)])
    operator = gpu.operator
    device_pointer = operator.values().data_ptr()
    drive = {(0, 3): np.asarray([180., 90.], dtype=np.float32)}
    kwargs = dict(steps=100, gains=np.ones(cpu.n_types, dtype=np.float32),
                  record={"all": np.arange(8)}, seed=29, spike_log=True)
    first = gpu.run(drive, **kwargs)
    gpu.run({(7,): 9000.0}, **kwargs)  # An intervening window must not carry state.
    again = gpu.run(drive, **kwargs)
    assert_contract_and_exact(first, again)
    assert_contract_and_exact(cpu.run(drive, **kwargs), first)
    without_log = gpu.run(drive, **{**kwargs, "spike_log": False})
    assert "_spikes" not in without_log
    assert set(without_log) == set(first) - {"_spikes"}
    assert gpu.operator is operator and gpu.operator.values().data_ptr() == device_pointer


def test_non_one_gains_are_rejected(tmp_path, cuda):
    cpu, gpu = pair(tmp_path, cuda)
    gains = np.ones(cpu.n_types, dtype=np.float32)
    gains[0] = 0.5
    with pytest.raises(ValueError, match="gain|one"):
        gpu.run({}, steps=100, gains=gains)


def test_mismatched_drive_lengths_are_rejected(tmp_path, cuda):
    cpu, gpu = pair(tmp_path, cuda)
    drive = {(0, 1, 2): np.asarray([100., 200.], dtype=np.float32)}
    with pytest.raises(ValueError) as reference:
        cpu.run(drive, steps=100)
    with pytest.raises(ValueError, match="drive|rates|match|length") as actual:
        gpu.run(drive, steps=100)
    assert type(actual.value) is type(reference.value)
