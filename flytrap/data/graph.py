"""Pure FlyEM graph construction. Both matrices use W[post, pre] indexing.

Duplicate pairs are summed before thresholding. Anatomical int64 counts retain
modulatory edges that have zero fast weight. Only Traced, non-Glia endpoints
survive; all eligible annotated bodies remain, including isolated neurons.
"""

from dataclasses import dataclass
from numbers import Integral, Real
from typing import Mapping

import numpy as np
import pandas as pd
import scipy.sparse as sp

MV_PER_SYNAPSE = 0.275
MIN_SYN = 3
SIGN = {
    "acetylcholine": 1.0, "gaba": -1.0, "glutamate": -1.0,
    "dopamine": 0.0, "octopamine": 0.0, "serotonin": 0.0,
    "histamine": -1.0, "unclear": 0.0, "unknown": 0.0,
}
TEXT_KEYS = ("types", "nt", "superclass", "subclass", "receptor", "fru")


@dataclass
class GraphData:
    W: sp.csr_matrix
    anatomy: sp.csr_matrix
    bodies: np.ndarray
    metadata: dict[str, np.ndarray]
    stats: dict[str, int]
    min_syn: int

    def arrays(self) -> dict[str, np.ndarray]:
        """Retain upstream NPZ keys and add the separate anatomical CSR."""
        return {
            "data": self.W.data, "indices": self.W.indices, "indptr": self.W.indptr,
            "shape": np.asarray(self.W.shape, dtype=np.int64), "bodies": self.bodies,
            **self.metadata,
            "anatomy_data": self.anatomy.data, "anatomy_indices": self.anatomy.indices,
            "anatomy_indptr": self.anatomy.indptr,
        }


def _threshold(min_syn: int) -> int:
    if isinstance(min_syn, bool) or not isinstance(min_syn, Integral) or min_syn < 1:
        raise ValueError("min_syn must be a positive integer")
    if min_syn > np.iinfo(np.int64).max:
        raise ValueError("min_syn exceeds int64")
    return int(min_syn)


def _required(frame: pd.DataFrame, names: tuple[str, ...], label: str) -> None:
    if not isinstance(frame, pd.DataFrame) or not frame.columns.is_unique:
        raise ValueError(f"{label} must be a DataFrame with unique columns")
    missing = set(names) - set(frame.columns)
    if missing:
        raise ValueError(f"{label} missing columns: {sorted(missing)}")


def _integers(series: pd.Series, label: str) -> np.ndarray:
    if pd.api.types.is_bool_dtype(series.dtype) or (
        series.dtype == object and any(isinstance(value, (bool, np.bool_)) for value in series)
    ):
        raise ValueError(f"{label} must contain nonnegative int64 integers, not booleans")
    if series.dtype == object and any(not isinstance(value, Real) for value in series):
        raise ValueError(f"{label} must contain numbers, not strings or missing values")
    if pd.api.types.is_string_dtype(series.dtype) and series.dtype != object:
        raise ValueError(f"{label} must contain numbers, not strings")
    try:
        values = pd.to_numeric(series, errors="raise").to_numpy()
        if values.dtype.kind not in "iuf" or not np.isfinite(values).all():
            raise ValueError("nonfinite or nonnumeric values")
        if (values < 0).any() or (values >= 2**63).any():
            raise ValueError("outside nonnegative int64 range")
        if values.dtype.kind == "f" and (
            (values != np.floor(values)).any() or (values > 2**53).any()
        ):
            raise ValueError("fractional or imprecisely represented integer")
        return values.astype(np.int64)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{label} must contain nonnegative int64 integers: {exc}") from exc


def _text(frame: pd.DataFrame, key: str) -> pd.Series:
    if key not in frame:
        return pd.Series("", index=frame.index, dtype=str)
    return frame[key].fillna("").astype(str).str.strip()


def _deduplicate(frame: pd.DataFrame, key: str, label: str) -> pd.DataFrame:
    distinct = frame.drop_duplicates()
    if distinct[key].duplicated().any():
        raise ValueError(f"conflicting duplicate {label} records")
    return distinct.set_index(key)


def _selected_annotations(annotations: pd.DataFrame) -> pd.DataFrame:
    _required(annotations, ("bodyId", "status"), "annotations")
    ann = pd.DataFrame({"bodyId": _integers(annotations["bodyId"], "bodyId")})
    for key in ("status", "statusLabel", "type", "flywireType", "instance",
                "superclass", "subclass", "receptorType", "fruDsx"):
        ann[key] = _text(annotations, key).to_numpy()
    ann = _deduplicate(ann, "bodyId", "annotation")
    ann = ann.loc[(ann["status"] == "Traced") & (ann["statusLabel"] != "Glia")].sort_index()
    if not len(ann):
        raise ValueError("no eligible Traced non-Glia bodies")
    return ann


def selected_bodies(annotations: pd.DataFrame) -> np.ndarray:
    """Validate metadata and return the stable body mapping for streamed filtering."""
    return _selected_annotations(annotations).index.to_numpy(dtype=np.int64)


def validate_weights(weights: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Validate every row before streamed endpoint filtering; return pre/post/counts."""
    _required(weights, ("body_pre", "body_post", "weight"), "weights")
    return (_integers(weights["body_pre"], "body_pre"),
            _integers(weights["body_post"], "body_post"), _integers(weights["weight"], "weight"))


def _fast(anatomy: sp.csr_matrix, sign: np.ndarray) -> sp.csr_matrix:
    result = anatomy.astype(np.float32)
    result.data *= np.float32(MV_PER_SYNAPSE)
    result.data *= sign[result.indices]
    result.eliminate_zeros()
    return result


def _stats(graph: GraphData) -> dict[str, int]:
    return {
        "bodies": len(graph.bodies), "anatomical_edges": graph.anatomy.nnz,
        "anatomical_synapses": int(graph.anatomy.data.sum()), "fast_edges": graph.W.nnz,
        "excitatory_edges": int((graph.W.data > 0).sum()),
        "inhibitory_edges": int((graph.W.data < 0).sum()),
        "zero_fast_edges": graph.anatomy.nnz - graph.W.nnz,
        "missing_types": int((graph.metadata["types"] == "").sum()),
        "unknown_nt_bodies": int((graph.metadata["nt"] == "unknown").sum()),
        "unsupported_nt_bodies": int(sum(x not in SIGN for x in graph.metadata["nt"])),
    }


def build_graph(
    weights: pd.DataFrame, annotations: pd.DataFrame, neurotransmitters: pd.DataFrame,
    *, min_syn: int = MIN_SYN,
) -> GraphData:
    """Validate tables and construct stable body mappings without max-ID arrays.

    Missing type falls back through type/flywireType/instance to empty. Missing
    NT becomes unknown; unsupported NT is retained with zero fast sign. Equal
    duplicate metadata rows collapse; conflicting rows fail. statusLabel is an
    optional upstream field; when present, its Glia label excludes the body.
    Unmapped/untraced/glial edge endpoints are excluded and counted.
    """
    min_syn = _threshold(min_syn)
    _required(neurotransmitters, ("body", "consensus_nt"), "neurotransmitters")
    pre, post, counts = validate_weights(weights)
    # A total bound prevents pair and downstream row-sum overflow without object arrays.
    if np.sum(counts, dtype=np.longdouble) > np.iinfo(np.int64).max:
        raise ValueError("synapse count total exceeds int64")
    ann = _selected_annotations(annotations)
    bodies = ann.index.to_numpy(dtype=np.int64)
    nt = pd.DataFrame({"body": _integers(neurotransmitters["body"], "neurotransmitter body")})
    nt["nt"] = _text(neurotransmitters, "consensus_nt").str.lower().replace("", "unknown").to_numpy()
    nt = _deduplicate(nt, "body", "neurotransmitter")
    nt_strings = nt["nt"].reindex(bodies).fillna("unknown").to_numpy(dtype=str)
    types = ann["type"].mask(ann["type"] == "", ann["flywireType"])
    types = types.mask(types == "", ann["instance"])
    metadata = {"types": types.to_numpy(dtype=str), "nt": nt_strings,
                "sign": np.asarray([SIGN.get(s, 0.0) for s in nt_strings], dtype=np.float32)}
    for target, source in (("superclass", "superclass"), ("subclass", "subclass"),
                           ("receptor", "receptorType"), ("fru", "fruDsx")):
        metadata[target] = ann[source].to_numpy(dtype=str)
    c, r = np.searchsorted(bodies, pre), np.searchsorted(bodies, post)
    mapped = (c < len(bodies)) & (r < len(bodies))
    mapped &= bodies[np.minimum(c, len(bodies) - 1)] == pre
    mapped &= bodies[np.minimum(r, len(bodies) - 1)] == post
    anatomy = sp.csr_matrix((counts[mapped], (r[mapped], c[mapped])), shape=(len(bodies), len(bodies)))
    anatomy.sum_duplicates()
    pairs_before_threshold = anatomy.nnz
    anatomy.data[anatomy.data < min_syn] = 0
    anatomy.eliminate_zeros()
    anatomy.sort_indices()
    if not anatomy.nnz:
        raise ValueError("no anatomical edges survive endpoint policy and min_syn threshold")
    graph = GraphData(_fast(anatomy, metadata["sign"]), anatomy, bodies, metadata, {}, min_syn)
    graph.stats = _stats(graph) | {
        "input_edge_rows": len(weights), "excluded_endpoint_rows": int((~mapped).sum()),
        "mapped_edge_rows": int(mapped.sum()), "aggregated_pairs_before_threshold": pairs_before_threshold,
        "pairs_below_threshold": pairs_before_threshold - anatomy.nnz,
        "duplicate_edge_rows": int(mapped.sum()) - pairs_before_threshold,
    }
    return graph


def anatomy_inputs(graph: GraphData) -> dict[str, np.ndarray]:
    """Report anatomical input dominance, a heuristic rather than compartment truth."""
    types = graph.metadata["types"]
    mbon = np.flatnonzero(np.char.startswith(types, "MBON"))
    pam = np.flatnonzero(np.char.startswith(types, "PAM"))
    ppl1 = np.flatnonzero(np.char.startswith(types, "PPL1"))
    pam_counts = np.asarray(graph.anatomy[mbon][:, pam].sum(axis=1)).ravel().astype(np.int64)
    ppl1_counts = np.asarray(graph.anatomy[mbon][:, ppl1].sum(axis=1)).ravel().astype(np.int64)
    labels = np.full(len(mbon), "tie", dtype="U4")
    labels[pam_counts > ppl1_counts] = "PAM"
    labels[ppl1_counts > pam_counts] = "PPL1"
    labels[(pam_counts == 0) & (ppl1_counts == 0)] = "zero"
    return {"mbon_bodies": graph.bodies[mbon], "pam_counts": pam_counts,
            "ppl1_counts": ppl1_counts, "classification": labels}


def graph_from_arrays(arrays: Mapping[str, np.ndarray], *, min_syn: int = MIN_SYN) -> GraphData:
    """Reconstruct only canonical, aligned graphs consistent with anatomical counts."""
    min_syn = _threshold(min_syn)
    required = {"data", "indices", "indptr", "shape", "bodies", "sign", *TEXT_KEYS,
                "anatomy_data", "anatomy_indices", "anatomy_indptr"}
    if required - set(arrays):
        raise ValueError(f"graph missing arrays: {sorted(required - set(arrays))}")
    if set(arrays) - required:
        raise ValueError(f"graph has unknown arrays: {sorted(set(arrays) - required)}")
    bodies = np.asarray(arrays["bodies"])
    if bodies.ndim != 1 or bodies.dtype != np.dtype("int64") or not len(bodies):
        raise ValueError("bodies must be a nonempty int64 vector")
    if (bodies < 0).any() or (bodies[1:] <= bodies[:-1]).any():
        raise ValueError("body mapping must be nonnegative, sorted and unique")
    n = len(bodies)
    shape = np.asarray(arrays["shape"])
    if shape.shape != (2,) or shape.dtype.kind not in "iu" or not np.array_equal(shape, [n, n]):
        raise ValueError("graph shape does not match bodies")
    metadata = {key: np.asarray(arrays[key]) for key in (*TEXT_KEYS, "sign")}
    for key, value in metadata.items():
        if value.shape != (n,) or (key != "sign" and value.dtype.kind != "U"):
            raise ValueError(f"invalid aligned metadata: {key}")
    sign = metadata["sign"]
    expected_sign = np.asarray([SIGN.get(x, 0.0) for x in metadata["nt"]], dtype=np.float32)
    if sign.dtype != np.float32 or not np.array_equal(sign, expected_sign):
        raise ValueError("fast sign metadata disagrees with neurotransmitters")
    for nt in metadata["nt"]:
        if not nt or nt != nt.strip().lower():
            raise ValueError("neurotransmitter metadata must be normalized")

    def csr(prefix: str, dtype: np.dtype) -> sp.csr_matrix:
        data, indices, indptr = (np.asarray(arrays[prefix + key]) for key in ("data", "indices", "indptr"))
        if data.ndim != 1 or data.dtype != dtype or indices.shape != data.shape:
            raise ValueError(f"invalid {prefix}CSR data")
        if indices.dtype.kind not in "iu" or indptr.dtype.kind not in "iu" or indptr.shape != (n + 1,):
            raise ValueError(f"invalid {prefix}CSR indices/indptr")
        if indptr[0] != 0 or indptr[-1] != len(data) or (indptr[1:] < indptr[:-1]).any():
            raise ValueError(f"invalid {prefix}CSR row pointers")
        if (indices < 0).any() or (indices >= n).any() or not np.isfinite(data).all() or (data == 0).any():
            raise ValueError(f"invalid {prefix}CSR values or column indices")
        result = sp.csr_matrix((data.copy(), indices.copy(), indptr.copy()), shape=(n, n))
        if not result.has_canonical_format:
            raise ValueError(f"{prefix}CSR must have sorted unique column indices")
        return result

    W = csr("", np.dtype("float32"))
    anatomy = csr("anatomy_", np.dtype("int64"))
    if not anatomy.nnz or (anatomy.data < min_syn).any():
        raise ValueError("anatomy is empty or violates min_syn threshold")
    if np.sum(anatomy.data, dtype=np.longdouble) > np.iinfo(np.int64).max:
        raise ValueError("anatomical synapse count total exceeds int64")
    expected = _fast(anatomy, sign)
    if not (np.array_equal(W.indptr, expected.indptr) and np.array_equal(W.indices, expected.indices)
            and np.array_equal(W.data, expected.data)):
        raise ValueError("fast weights disagree with anatomy and transmitter signs")
    graph = GraphData(W, anatomy, bodies.copy(), metadata, {}, min_syn)
    graph.stats = _stats(graph)
    return graph
