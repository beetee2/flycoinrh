"""Read-only host discovery; never open a video device or import the model."""
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import re
import selectors
import shutil
import stat
import subprocess
import threading
import time

from .contracts import SourceCapability


REPO = Path(__file__).resolve().parents[2]
BACKEND = "ffmpeg-v4l2"
MAX_METADATA_BYTES = 65_536


def _text(path: Path) -> str | None:
    try:
        with path.open("rb") as stream:
            value = stream.read(4097)
        if len(value) > 4096:
            return None
        return value.decode("utf-8", errors="replace").strip()
    except OSError:
        return None


def _label(value: str | None) -> str | None:
    if value is None:
        return None
    value = "".join(character for character in value if character.isprintable()).strip()[:128]
    return value or None


def discover_devices(sysfs: Path = Path("/sys/class/video4linux"),
                     dev_root: Path = Path("/dev")) -> dict:
    """List sysfs metadata only; stat does not open the device for capture."""
    devices, errors = [], []
    try:
        entries = sorted(sysfs.iterdir(), key=lambda entry: entry.name)
    except FileNotFoundError:
        entries = []
        errors.append("No video4linux sysfs class exists; no capture device is available.")
    except OSError:
        entries = []
        errors.append("Video device metadata is inaccessible; check operator access to sysfs.")
    for entry in entries:
        if not re.fullmatch(r"video[0-9]{1,53}", entry.name):
            continue
        name = _label(_text(entry / "name"))
        driver = None
        for candidate in (entry / "device/driver", entry / "device/driver/module"):
            try:
                if candidate.is_symlink():
                    driver = candidate.resolve(strict=True).name
                    break
            except OSError:
                pass
        # Virtual devices often expose their driver in uevent rather than a driver link.
        uevent = _text(entry / "device/uevent") or ""
        if driver is None:
            driver = next((line[7:] for line in uevent.splitlines() if line.startswith("DRIVER=")), None)
        driver = _label(driver)
        path = dev_root / entry.name
        try:
            is_character_device = stat.S_ISCHR(path.stat().st_mode)
            accessible = is_character_device and os.access(path, os.R_OK | os.W_OK)
        except OSError:
            is_character_device, accessible = False, False
        if name is None or not is_character_device:
            errors.append(f"Incomplete metadata or missing character device for {entry.name}.")
        elif not accessible:
            errors.append(f"Read/write access unavailable for {entry.name}; operator setup is required.")
        capability = SourceCapability(
            schema_version="obs-source-1", source_id=f"v4l2-{entry.name}", evidence_kind="real",
            name=name or entry.name, driver=driver, backend=BACKEND, capabilities=None, formats=None,
            metadata_state="partial", producer_detection="unknown",
        )
        devices.append({
            "source_id": capability.source_id, "name": name, "driver": driver,
            "capability": capability.model_dump(mode="json"),
            "character_device": is_character_device, "read_write_access": accessible,
            "capabilities": None, "formats": None, "selected": False,
            "inspection": "sysfs-only",
            "detail": "Capabilities/formats unknown: ioctl inspection awaits explicit source selection.",
        })
    if not devices and not errors:
        errors.append("No video devices are registered; enable an operator-approved OBS virtual device.")
    return {"schema_version": "flyjam-live-device-discovery-1", "devices": devices,
            "errors": errors, "capture_started": False, "real_obs_gate": "not_run",
            "status": "blocked" if errors else "ok"}


def metadata_command(arguments: list[str], *, timeout: float = 5.0) -> dict:
    """Run fixed metadata arguments with a deadline and a hard output cap."""
    executable = shutil.which(arguments[0])
    result = {"command": arguments, "executable": executable, "exit_code": None, "output": ""}
    if executable is None:
        return {**result, "status": "missing"}
    child = None
    output = bytearray()
    try:
        child = subprocess.Popen([executable, *arguments[1:]], stdin=subprocess.DEVNULL,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False)
        deadline = time.monotonic() + timeout
        with selectors.DefaultSelector() as selector:
            selector.register(child.stdout, selectors.EVENT_READ)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError
                for key, _ in selector.select(min(remaining, 0.1)):
                    chunk = os.read(key.fileobj.fileno(), min(4096, MAX_METADATA_BYTES + 1 - len(output)))
                    if not chunk:
                        selector.unregister(key.fileobj)
                    output.extend(chunk)
                    if len(output) > MAX_METADATA_BYTES:
                        raise OverflowError
        result["exit_code"] = child.wait(timeout=max(0.001, deadline - time.monotonic()))
        result["status"] = "ok" if result["exit_code"] == 0 else "failed"
    except (TimeoutError, subprocess.TimeoutExpired):
        result["status"] = "timeout"
    except OverflowError:
        result["status"] = "output_limit"
    except OSError:
        result["status"] = "unavailable"
    finally:
        if child is not None:
            if child.poll() is None:
                child.kill()
            try:
                result["exit_code"] = child.wait(timeout=.5)
            except subprocess.TimeoutExpired:
                result["status"] = "cleanup_timeout"
                # Uninterruptible kernel IO cannot be repaired by this process.
                # Keep the caller bounded and reap if/when the kernel releases it.
                threading.Thread(target=child.wait, daemon=True).start()
            if child.stdout is not None:
                child.stdout.close()
    # Strip terminal controls from locally installed program output.
    decoded = output[:MAX_METADATA_BYTES].decode("utf-8", errors="replace")
    result["output"] = "".join(c for c in decoded if c in "\n\t" or c.isprintable())
    return result


def _identity(path: Path) -> dict:
    try:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return {"status": "ok", "bytes": path.stat().st_size, "sha256": digest.hexdigest()}
    except OSError:
        return {"status": "unavailable", "bytes": None, "sha256": None}


def inspect_model_identity(repo: Path = REPO) -> dict:
    """Check pinned bytes and source identities without graph loading or inference."""
    paths = {
        "graph": "build/flytrap-v1/graph.npz", "manifest": "build/flytrap-v1/manifest.json",
        "checkpoint": "artifacts/milestones/05/trials/baseline.json",
        "annotations": "data/body-annotations.feather",
        "neurotransmitters": "data/body-neurotransmitters.feather",
        "weights": "data/connectome-weights.feather",
        "parameters": "config/flytrap-model-v1.json", "calibration": "config/flytrap-visual-v1.json",
        "flysim": "flysim.py", "flyeye": "flyeye.py", "adapter": "flytrap/controllers/fly.py",
    }
    identities = {key: {"path": path, **_identity(repo / path)} for key, path in paths.items()}
    errors = [f"Missing or unreadable {key}." for key, value in identities.items()
              if value["status"] != "ok"]
    try:
        def read_json(relative):
            with (repo / relative).open("rb") as stream:
                payload = stream.read(65_537)
            if len(payload) > 65_536:
                raise ValueError("metadata size limit")
            return json.loads(payload)
        manifest = read_json(paths["manifest"])
        checkpoint = read_json(paths["checkpoint"])
        catalog = read_json("flytrap/data/sources.json")
        if manifest["source"] != catalog or catalog["fixture"] is not False:
            errors.append("Graph does not declare the pinned full real dataset.")
        if checkpoint["fixture"] is not False or checkpoint["neural_state_mode"] != "windowed_reset":
            errors.append("Checkpoint is not the unchanged real windowed_reset baseline.")
        if checkpoint["learning_enabled"] is not False or checkpoint["gains"] != "all-one-float32":
            errors.append("Checkpoint baseline gains/learning declaration is incompatible.")
        for key in ("graph", "annotations", "parameters", "calibration"):
            if identities[key]["sha256"] != checkpoint[f"{key}_sha256"]:
                errors.append(f"Checkpoint {key} identity mismatch.")
        if identities["graph"]["sha256"] != manifest["graph_sha256"]:
            errors.append("Graph manifest hash mismatch.")
        for key in ("flysim", "flyeye", "adapter"):
            if identities[key]["sha256"] != checkpoint["model_source_sha256"][key]:
                errors.append(f"Checkpoint {key} source identity mismatch; do not regenerate silently.")
        for key in ("annotations", "neurotransmitters", "weights"):
            expected = next(item for item in catalog["files"] if item["filename"] == Path(paths[key]).name)
            if (identities[key]["sha256"] != expected["sha256"]
                    or identities[key]["bytes"] != expected["size_bytes"]):
                errors.append(f"Pinned raw {key} identity mismatch.")
    except (OSError, ValueError, KeyError, TypeError, StopIteration):
        errors.append("Model identity metadata is missing, oversized, malformed, or incomplete.")
    return {"status": "blocked" if errors else "ok", "files": identities, "errors": errors,
            "model_loaded": False, "neural_calls": 0,
            "scope": "Byte/source identity inspection only; real-model execution gate is not run."}


def inspect_environment(repo: Path = REPO) -> dict:
    commands = {
        "ffmpeg": ["ffmpeg", "-version"], "ffmpeg_devices": ["ffmpeg", "-hide_banner", "-devices"],
        "ffmpeg_v4l2": ["ffmpeg", "-hide_banner", "-h", "demuxer=v4l2"],
        "v4l2_ctl": ["v4l2-ctl", "--version"], "obs": ["obs", "--version"],
        "node": ["node", "--version"], "npm": ["npm", "--version"],
        "git_head": ["git", "-C", str(repo), "rev-parse", "HEAD"],
    }
    tools = {key: metadata_command(args) for key, args in commands.items()}
    supported = (tools["ffmpeg_v4l2"]["status"] == "ok"
                 and "Demuxer video4linux2,v4l2" in tools["ffmpeg_v4l2"]["output"]
                 and tools["ffmpeg_devices"]["status"] == "ok"
                 and any(re.match(r"\s*D[ E]*\s+video4linux2,v4l2\s", line)
                         for line in tools["ffmpeg_devices"]["output"].splitlines()))
    packages = {}
    for name in ("fastapi", "pydantic", "uvicorn", "numpy", "scipy", "pandas", "pyarrow", "Pillow"):
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = None
    devices = discover_devices()
    model = inspect_model_identity(repo)
    blockers = list(devices["errors"])
    if not supported:
        blockers.append("Install/provide FFmpeg with the V4L2 demuxer before OBS01 capture validation.")
    if tools["obs"]["status"] != "ok":
        blockers.append("OBS is unavailable; operator must provide OBS before real-source validation.")
    if model["status"] != "ok":
        blockers.extend(model["errors"])
    if any(value is None for value in packages.values()):
        blockers.append("Required Python service/model packages are missing from this interpreter.")
    if tools["node"]["status"] != "ok" or tools["npm"]["status"] != "ok":
        blockers.append("Node/npm are unavailable for local frontend checks.")
    disk = shutil.disk_usage(repo)
    return {
        "schema_version": "flyjam-live-doctor-1", "status": "blocked" if blockers else "ok",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "system": {"platform": platform.system(), "kernel": platform.release(),
                   "machine": platform.machine(), "distribution": _text(Path("/etc/os-release")),
                   "python": platform.python_version(), "packages": packages,
                   "disk_total_bytes": disk.total, "disk_free_bytes": disk.free,
                   "v4l2loopback_loaded": Path("/sys/module/v4l2loopback").is_dir()},
        "tools": tools, "backend": {"id": BACKEND, "installed_support": supported,
                                     "capture_implemented": True},
        "devices": devices, "model_identity": model, "blockers": blockers,
        "operator_setup": [
            "Select an OBS virtual camera explicitly before any device ioctl, preview or capture.",
            "If no virtual camera exists, configure OBS/v4l2loopback through the operator; privileged setup requires approval.",
            "After selection, OBS01 must inspect formats/driver and test producer-stop detection; this is unverified.",
        ],
        "capture_started": False, "neural_calls": 0,
    }
