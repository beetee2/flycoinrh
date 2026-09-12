# Explicit baseline controller

Milestone 03 provides a local `FlyController` with the existing 16×16 Observation
and ControllerOutput contracts. It uses upstream FlyEye, FlyPilot and FlyBrain.
Its operator inputs are explicit graph-bundle, annotation, model-parameter,
calibration and checkpoint paths. Paths resolve during construction; subsequent
reset/step calls need no current-directory files. The worker integration remains
milestone 07.

## Create and inspect the baseline

From the checkout, after `make data-doctor`, create a new descriptor at a path
whose parent already exists:

```sh
.venv/bin/python -m flytrap.cli controller-baseline --graph-root build/flytrap-v1 --annotations-path data/body-annotations.feather --parameters-path config/flytrap-model-v1.json --calibration-path config/flytrap-visual-v1.json --checkpoint-path artifacts/local/baseline-v1.json
.venv/bin/python -m flytrap.cli controller-doctor --graph-root build/flytrap-v1 --annotations-path data/body-annotations.feather --parameters-path config/flytrap-model-v1.json --calibration-path config/flytrap-visual-v1.json --checkpoint-path artifacts/local/baseline-v1.json
make test-controller-real EVIDENCE=artifacts/milestones/03
```

Creation refuses an existing file. The checkpoint records an untrained baseline
with all-one float32 gains and learning disabled. It binds graph, annotation,
parameter-file, calibration-file and model-source hashes. Byte changes, including
configuration formatting, require a new descriptor. Paths can be relocated without
changing identity. Operator tools reject fixtures. Tests may explicitly opt into
a fixture graph; its checkpoint and output remain labeled `fixture` even though
they execute the neural engine. Provenance separately names `windowed_reset`.

`controller-doctor` verifies loading and reports populations/provenance. It does
not execute a simulation. `make test-controller-real` executes neural windows and
fails when real inputs are missing. The full `make verify-real` release gate stays
blocked until the later arena/worker/API/replay/browser integration exists.

## Evaluation boundary and declared mappings

Call `reset(run_seed=..., checkpoint=controller.checkpoint)` before `step`.
Run seeds are unsigned 32-bit integers. Per-step seeds are the first eight bytes
of SHA256, interpreted as an unsigned big-endian integer, over:

```text
b"FLYTRAP-step-seed-v1\0" || u32be(run_seed) || u64be(zero_based_step_index)
```

Pixels do not influence this seed stream. Each upstream run resets membrane
potential and refractory state. A reset restarts the stream and all-one gains.
Model failures invalidate the active run until another explicit reset; exceptions
propagate. No persisted mushroom state, upstream calibrated gains, environment
variables, target coordinates or task labels are read by the controller.

The input is normalized grayscale, row-major, converted to float32. FlyEye samples
the 16×16 raster at fixed center `(8,8)` and FOV `(16,16)`. Each retina coordinate
uses `min(15, max(0, trunc(16*u)))` and the corresponding `v` index. Sampling matches
upstream FlyEye on that raster, including endpoint clipping. It does **not** imply
that any arbitrary interior crop equals upstream full-scene sampling: an endpoint
at `u=1` would request the next pixel in an unpadded full scene. Milestone 04 must
define the authoritative crop and preserve these clipped observation semantics.

L1 light input is multiplied by 180 Hz; L2 darkness input by 180×0.6 Hz. These
are declared untrained settings, not visual-task calibration results. Required
populations are finite-coordinate L1/L2, bilateral DNa02 and DNa01, MDN, DNp09 and
MN9. Cells lacking a retinal coordinate remain excluded as upstream does;
provenance reports the excluded counts. Infinite coordinates, empty required
populations, malformed settings and nonfinite outputs fail.

Upstream steering is `(steer_R-steer_L)/450`; forward drive is the mean bilateral
DNa01 rate divided by 450. MDN subtracts backward drive, and DNp09 suppresses
speed. Divide FlyPilot's final displacement by 90 to produce bounded `dx,dy` in
[-1,1]. Positive `dy` is downward/backward. Click retains the DNp09 ≥330 Hz and
speed <0.25 rule. No trajectory correction or task success rule exists here.

Telemetry reports exact spikes counted over every model neuron, sampled-neuron
count and `sim_steps*dt` neural milliseconds. Wall time is measured separately in
test evidence. Defaults use 100 steps ×0.2 ms =20 ms per window. No real-time or
learning-improvement claim follows from these measurements.

`step_serialized` accepts only Observation JSON bytes, at most 32,768 bytes, and
returns ControllerOutput JSON bytes. Unknown fields and mutated/bypassed model
objects fail validation. This is the envelope for future simulator IPC; it is not
a durable worker or a sandbox against malicious code with host access.

## Evidence

See [milestone 03](milestones/03.md), including synthetic and real-model results,
installed-wheel execution from an unrelated directory, mutation probes and
measured timing. Root upstream modules are included in the built wheel so the
adapter works independently of a repository-root import path.
