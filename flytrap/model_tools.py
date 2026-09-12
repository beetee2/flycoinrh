"""Local operator tools for the explicit baseline adapter, separate from release gates."""
import time

from flytrap.controllers.fly import FlyController, write_baseline_checkpoint


def run_command(command, *, graph_root, annotations_path, parameters_path, calibration_path, checkpoint_path):
    paths = dict(graph_root=graph_root, annotations_path=annotations_path, parameters_path=parameters_path,
                 calibration_path=calibration_path, checkpoint_path=checkpoint_path)
    if command == "controller-baseline":
        checkpoint = write_baseline_checkpoint(**paths)
        return {"status": "PASS", "checkpoint": checkpoint.model_dump(),
                "checkpoint_path": str(checkpoint_path.resolve()), "learning_enabled": False}
    started = time.perf_counter()
    controller = FlyController(**paths)
    return {"status": "PASS", "gate": "adapter_load_only", "provenance": controller.provenance,
            "load_wall_seconds": time.perf_counter() - started,
            "simulation_executed": False, "release_ready": False}
