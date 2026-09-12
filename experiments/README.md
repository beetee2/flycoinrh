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
