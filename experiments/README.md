# FLYTRAP development experiments

`feasibility-v1.json` declares milestone 05's development-only design. The full
model, graph, retina, reset behavior and default all-one gains are unchanged.
No held-out task families or training checkpoints are used. Seeds 51001 and
51002 are development seeds and must not later be described as held-out data.

Run from the repository root with the locked environment and verified raw data:

```sh
make data-doctor
make feasibility EVIDENCE=artifacts/milestones/05
make verify-feasibility EVIDENCE=artifacts/milestones/05
```

The trial output directory must be absent. To rerun, select a new evidence root;
retain previous evidence. The runner creates an explicit baseline checkpoint and
refuses fixture graphs. A missing graph fails with a nonzero exit and preserves
its diagnostic report. The independent verifier checks completeness, hashes,
model labels, recorded metrics, observation sampling and action-to-physics replay.
It does not re-execute the neural model or establish biological fidelity.

Two seeds × seven input conditions × two repetitions produce 28 actual neural
windows. Every probe resets the same checkpoint to the same run seed before its
first window. Conditions are dark, bright, midgray, alternating stripes,
checkerboard, and the initial canonical crop for each pad layout. Comparisons
pair seeds and distinguish changed input hashes, motor outputs, click telemetry
and neural activity. Equal repeated outputs establish local repeatability;
differences across matched inputs establish sensitivity, not learning.

Two seeds × four episode conditions produce eight complete development episodes:
stripes-left, stripes-right, dark-input stripes-left, and half-speed stripes-left.
The dark control supplies 256 zero pixels on every step; it retains the same
scored world but cannot see it. The scaling variant explicitly multiplies both
real motor axes by 0.5 before the existing physics. It records raw and applied
actions. There is no sign change, attraction or trajectory correction. The
canonical condition applies a multiplier of 1.0. Neither control is a supported
public product option.

Every episode uses zero distractions, the fixed lower start and existing pad
geometry. Stripes are rewarded in both swapped layouts. Episodes stop on scored
pad contact or at 256 ticks. A simulation exception is a failed execution, never
a scored timeout. Complete ordered traces preserve initial/final state, raw and
applied outputs, wall duration and the SHA256 of 256 raw observation bytes.
Canonical PNGs decode to the corresponding raw raster. Overlay PNGs are generated
from recorded coordinates after simulation; labels and paths are never inputs.

Cost measurements include baseline preparation, the first controller construction
in a fresh process, each serialized neural-window call, full episode duration,
and Linux process peak resident memory. OS caches are not evicted, and baseline
preparation reads the graph before controller construction. This is not a cold
storage benchmark. The measurements describe this workstation under its current
load; later container and worker gates must measure their own overhead and limits.
The empirical nearest-rank p95 is descriptive, not a tail-latency guarantee.

Stationary steps count unchanged quantized positions. Nonzero motor fraction
counts nonzero dx or dy even when a collision prevents movement. Total distance
sums actual consecutive state displacements. The longest stationary streak and
unique observation hashes expose prolonged wall trapping or sensory repetition.
All scheduled episodes, including failures and timeouts, must remain in reports.

## Milestone 05 human-review revision

`feasibility-revision-v2.json` predeclares one bounded development revision.
Historical v1 configurations, checkpoints, traces and verifier remain intact.
The new runner uses the same baseline checkpoint bytes and records six passive
motor population rates. Both versions retain positive-down y and the original
motor mapping. `tangent_v2` is an explicit opt-in physics candidate in
`flytrap/arena/sliding.py`; the default `arena.core.step` still uses v1.

The primary comparison schedules two fixed development seeds, both layouts,
canonical and black inputs, and both physics versions: 16 episodes of at most
96 ticks. A cutoff at 96 is **incomplete**, not a 256-tick scored timeout. Its
budget is 1,536 neural calls and 900 seconds including load. If at least half the
canonical candidate ticks sample no pad pixels, a separately recorded observation
comparison may run eight episodes with candidate physics, at most 768 calls and
450 seconds. All results are retained; no extensions or replacement seeds.

The one optional `overview16_v2` observation uses fixed full-scene nearest-center
samples at x,y = 3, 9, ..., 93. It retains visible scene cues throughout the path
and adds no position, avatar or scoring fields. Because the canonical scene is
static, this overview also stays constant within a layout; it supplies no visual
feedback about the avatar's changing position. That limitation must accompany
its behavioral results. The v1 crop stays available byte-for-byte.

Execution and artifact verification use `scripts.feasibility_revision` and
`scripts.verify_feasibility_revision`; each accepts an explicit `--output`.
The execution stage is `--stage physics` or `--stage overview`, with the latter
requiring completed primary evidence via `--primary`. A new evidence parent must
contain `preregistration.json` with the declared UTC timestamp, exact config and
SHA256 before execution; the verifier checks this ordering. Existing output
directories are refused. Retain the complete parent, including `primary/`, when
verifying `overview/`.

Read the [historical diagnosis](../docs/implementation/FEASIBILITY-05-DIAGNOSIS.md)
and [revision comparison](../docs/implementation/FEASIBILITY-05-REVISION.md).
This work does not authorize milestone 06 or establish task competence, learning,
or suitability for release.
