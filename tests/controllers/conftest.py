"""Explicitly synthetic connectomes for adapter boundary tests."""

import base64
import hashlib

import pandas as pd
import pytest

from flytrap.data.bundle import DatasetSource, file_sha256, write_bundle
from flytrap.data.graph import build_graph


@pytest.fixture
def adapter_files_factory(tmp_path):
    """Write independent, attributed tiny graphs with functioning visual/motor paths."""
    sequence = 0

    def create(*, missing_population=None, annotation_edit=None):
        from flytrap.controllers.fly import ModelParameters, VisualCalibration

        nonlocal sequence
        root = tmp_path / f"synthetic-adapter-{sequence}"
        sequence += 1
        root.mkdir()
        neurons = []
        for kind in ("L1", "L2"):
            for h1, h2 in ((0, 0), (2, 0), (0, 2), (2, 2)):
                neurons.append(dict(bodyId=len(neurons) + 1, type=kind, somaSide="L",
                                    assignedOlHex1=float(h1), assignedOlHex2=float(h2)))
        for kind, side in (("DNa02", "L"), ("DNa02", "R"), ("DNa01", "L"),
                           ("DNa01", "R"), ("MDN", "L"), ("DNp09", "R"), ("MN9", "L")):
            neurons.append(dict(bodyId=len(neurons) + 1, type=kind, somaSide=side,
                                assignedOlHex1=float("nan"), assignedOlHex2=float("nan")))
        annotations = pd.DataFrame(neurons)
        annotations["status"] = "Traced"
        annotations["statusLabel"] = ""
        if missing_population:
            kind, side = missing_population
            selected = annotations["type"] == kind
            if side is not None:
                selected &= annotations["somaSide"] == side
            annotations.loc[selected, "type"] = "OTHER"
        if annotation_edit is not None:
            annotation_edit(annotations)
        # Deliberately asymmetric routing makes the fixture's pixels affect actual
        # neural activity and signed motor output, rather than testing silent cells.
        weights = pd.DataFrame([
            {"body_pre": pre, "body_post": post, "weight": 100}
            for pre, targets in ((1, (9, 11)), (2, (10, 12)), (3, (9, 13)),
                                 (4, (10, 14)), (5, (9, 11)), (6, (10, 12)),
                                 (7, (13, 15)), (8, (14, 15)))
            for post in targets
        ])
        neurotransmitters = pd.DataFrame({"body": annotations["bodyId"], "consensus_nt": "acetylcholine"})
        sources = []
        for frame, name in ((weights, "connectome-weights.feather"),
                            (annotations, "body-annotations.feather"),
                            (neurotransmitters, "body-neurotransmitters.feather")):
            path = root / name
            frame.to_feather(path)
            payload = path.read_bytes()
            sources.append(dict(
                filename=name, url=f"synthetic:test/{name}", generation="fixture-1",
                size_bytes=len(payload), sha256=file_sha256(path),
                md5_base64=base64.b64encode(hashlib.md5(payload, usedforsecurity=False).digest()).decode(),
            ))
        source = DatasetSource(
            dataset="SYNTHETIC ADAPTER TEST ONLY", version="fixture-1", fixture=True,
            attribution="Hand-constructed 15-neuron graph; no biological behavior claim.",
            license="synthetic", reference_url="synthetic:adapter-tests", files=sources,
        )
        graph_root = root / "graph"
        write_bundle(build_graph(weights, annotations, neurotransmitters), graph_root, source)
        parameters_path = root / "parameters.json"
        calibration_path = root / "calibration.json"
        parameters_path.write_text(ModelParameters().model_dump_json())
        calibration_path.write_text(VisualCalibration().model_dump_json())
        return dict(
            graph_root=graph_root, annotations_path=root / "body-annotations.feather",
            parameters_path=parameters_path, calibration_path=calibration_path,
            checkpoint_path=root / "baseline.json", allow_fixture=True,
        )

    return create


@pytest.fixture
def adapter_files(adapter_files_factory):
    from flytrap.controllers.fly import write_baseline_checkpoint

    files = adapter_files_factory()
    write_baseline_checkpoint(**files)
    return files
