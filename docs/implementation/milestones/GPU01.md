# GPU01 — optional CUDA inference and measured A/B

2026-09-16. **Implementation and local qualification PASS. CPU remains the
default. Default promotion and manual OBS responsiveness review are PENDING.**
Capture, inference, benchmark browsers and owned services are stopped.

The user authorized this one GPU workstream, including local installation and
at most 384 additional full-graph attempts. It supersedes historical GPU
restrictions for GPU01 only. Starting checkout was clean at
`68bafc1de9682baee940c684de5fd6c44e270e0c`, which retains reviewed fork
`05dbb75744352e6767a1408af4874ebea6c9936e` and its newer operator-confirmation
documentation. The supplied GPU01 request is the task specification.

The candidate substantially reduces neural latency. Rendering did not improve
in this short run: its observed draw-interval p95 worsened. Keep CPU as the
default until the operator compares the same OBS scene and judges the tradeoff.
Neither latency nor these tests establish intelligence or entertaining movement.

| Boundary | Result |
|---|---|
| Optional dependencies / actual local CUDA | PASS |
| Exact-reference operation order / output types | PASS, 9 tiny-graph tests |
| Fixed full-graph numerical/control comparison | PASS, 18 pairs |
| Full-graph GPU repeatability | PASS, 18 exact repeats |
| Owned worker, failure handling and explicit backend | PASS |
| Accelerated visible Screen Gremlin A/B | PASS, 32 CPU + 32 GPU calls |
| Rendering improvement | Not established; measured p95 worsened |
| Manual OBS A/B / default promotion | PENDING operator review |

The machine has an NVIDIA GeForce RTX 3080, 10,240 MiB advertised VRAM,
driver 610.57.04, Intel i9-10900KF (20 logical CPUs), approximately 31.1 GiB
RAM, Linux 7.2.4 and Python 3.14.7. Initial `nvidia-smi` inspection showed
6,889 MiB free; memory changes with the existing desktop applications.
PyTorch was initially absent. Installed `torch==2.10.0+cu128` reports CUDA 12.8
available and identifies the RTX 3080. NumPy 2.4.2, SciPy 1.17.1 and all prior
dependency versions were retained. No driver, kernel or system package changed.

The `gpu` extra and `uv.lock` pin the optional Linux/x86-64 CUDA packages. The
PyTorch index is explicit and used only for Torch; the first attempted generic
index configuration failed resolution because it shadowed the existing Requests
pin, and was replaced before installation. Installation used:

```text
uv sync --locked --extra model --extra gpu --group upstream --inexact
```

CPU startup does not import Torch. Ordinary CPU CI excludes `tests/gpu`;
`make test-gpu` is a separate required-CUDA gate and fails when CUDA is absent.
The GPU live gate binds the tested numerical engine, Python/packages, historical
checkpoint, graph, GPU model, CUDA runtime and driver. Changed prerequisites
require requalification; GPU requests never become CPU sessions silently.

`flytrap/live/gpu.py` selectively adapts the CSR operator, simulation ordering,
NumPy randomness, duplicate-input handling and integer spike accumulation from
[upstream flysim_gpu.py at the reviewed revision](https://github.com/fruitflydev/flycoinrh/blob/f2fdedf49bbd2712834c5404c690670af26c2028/flysim_gpu.py).
Upstream `bench_gpu.py`, `build/gpu_bench.json` and tests were inspected. Their
calibrated/batched 60-step timing and nonsignificance comparison are not our gate.
The source attribution and repository LICENSE/NOTICE remain intact.

The adapter first verifies the historical CPU checkpoint and graph, then attaches
a separate CUDA execution object inside the owned worker. `flysim.py`,
`flyeye.py`, `flytrap/controllers/fly.py`, parameters, calibration, graph and
checkpoint are unchanged. Graph order, all-one gains, disabled learning, current
encoder/populations, SHA256 step-seed stream, 100 steps at 0.2 ms, window resets,
decoder, ground physics and presentation are preserved. Batch size is one.
The CSR operator stays on device; per-observation membrane state resets. Host
random draws retain the CPU call order and are transferred for that observation.
No video frames are batched. Membranes and sparse arithmetic are float32.

GPU output includes the actual Python integer `_total_spikes`, float64 population
rate arrays, ascending int64 `_fired`, Python float statistics and optional int32
spike logs. Execution provenance identifies `cuda-torch-csr-v1`, source hash,
device, dtype, libraries and effective configuration; GPU model IDs are distinct.
The service, launcher and UI explicitly select/label CPU or CUDA. Recordings
retain their execution descriptor, and historical recording hashes still verify.
The UI distinguishes the server backend from a loaded recording's backend.

The predefined plan was saved before confirmation calls at
`artifacts/milestones/GPU01/fixed-input/plan.json`. Seeds 17, 29 and 43 each use
black, white, gray, horizontal ramp, checkerboard and bar images, through the
production encoder and existing derived seed stream. Required equivalence was
exact spike totals, every recorded per-neuron population rate, fired indices,
raw actions, typed outputs and decoded controls at identical 500 ms application
intervals. Only final mean membrane voltage allowed absolute error 0.0001 mV,
relative tolerance zero, to accommodate float32 reduction rounding. GPU repeats
required exact equality. These conservative tolerances were not widened.

All 18 pairs passed; **every recorded difference was zero**, including mean
membrane voltage. All 18 GPU repeats matched exactly. The 40 MiB raw result
retains individual arrays, types, statistics and independent comparisons, rather
than only an aggregate result. This qualifies the tested safe set and environment,
not all possible inputs: CPU accumulates synapses in float64 before casting,
whereas cuSPARSE accumulates float32, so other threshold-sensitive inputs can
still diverge. The checked-in qualification manifest records plan/report hashes
and the exact numerical-engine hash. Later gating/provenance-only edits did not
change that engine; the final tiny-graph gate reconfirmed it.
The runtime gate verifies the engine/configuration prerequisites; full-source,
plan and report hashes are provenance references, not a requirement to reread
the private 40 MiB report at every startup.

CPU profiling ran before CUDA construction. The following fixed-input figures
exclude the first call of each backend (17 warm samples each); all calls,
including cold calls and repeats, remain charged. Milliseconds are median / p95.

| Stage | CPU | CUDA |
|---|---:|---:|
| Production encoding and Observation creation | 0.47 / 0.94 | 0.46 / 0.46 |
| Both durable ledgers and allowance checks | 21.75 / 28.14 | 21.25 / 29.01 |
| Neural run, including required result materialization | 512.54 / 799.50 | 48.82 / 54.02 |
| Remaining adapter/tap work | 2.14 / 2.59 | 1.79 / 2.07 |
| Encoding + ledger + whole adapter wall time | 551.94 / 824.84 | 72.42 / 83.92 |

Within CUDA, host input/random preparation measured 1.48 / 1.78 ms, device
setup/H2D 0.82 / 1.19 ms, neural event span 45.23 / 49.81 ms and D2H span
0.42 / 0.62 ms. CUDA events bracket stages, and synchronization precedes and
follows completed-work wall timing. Event spans include host launch gaps; these
are not isolated hardware-kernel durations. Required rates, spike counts, fired
indices and mean voltage are fully materialized. CPU materialization remains
inside its unchanged run timer. The model computation dominates CPU time;
durable accounting becomes a substantial GPU-path cost and was not weakened.

Verified graph/controller/retina startup took 4.46 s; CUDA import/operator/device
loading added 1.20 s in the same diagnostic process. Peak Torch tensor allocation
was 88,786,432 bytes (84.7 MiB), excluding driver/context allocations. Diagnostic
process maximum RSS was 754,000 KiB after CPU and 1,404,244 KiB after CUDA.

The actual A/B used installed Chrome **153.0.8010.36**, headed, with a visible
1280×900 Screen Gremlin page and ANGLE/NVIDIA RTX 3080 OpenGL ES 3.2. CPU ran
first, then CUDA, each on the same deterministic changing generated source,
seed 17, recording off, 120-second limit and 32-call cap. All 32 outputs were
observed for each backend. Both honestly stopped at the call cap; the GPU
active interval was shorter. Existing 120-second/512-call maximums were retained.

| Live measurement, median / p95 | CPU | CUDA |
|---|---:|---:|
| Session step wall time, n=32 | 506.05 / 554.93 ms | 94.80 / 102.32 ms |
| Accepted frame receipt → completion, n=32 | 520.62 / 570.19 ms | 109.53 / 127.34 ms |
| Response age at publication, n=32 | 550.01 / 586.18 ms | 134.97 / 171.27 ms |
| Completion → observed publication, n=32 | 27.74 / 48.31 ms | 31.51 / 51.40 ms |
| Browser neural receipt interval, n=31 | 506.0 / 558.0 ms | 100.7 / 102.3 ms |
| Display fetch header RTT, n=211 / 39 | 4.20 / 5.50 ms | 3.60 / 4.24 ms |
| Observed completed draw interval, n=1167 / 182 | 4.50 / 28.07 ms | 11.30 / 50.37 ms |

The live step median improved **5.34×**. Server completion cadence was about
1.96 versus 10.50 updates/s. Browser first-running status arrived 4.41 / 5.55 s
after Start; first neural response arrived 4.91 / 5.80 s. Service HTTP readiness
alone was 0.42 / 0.51 s. Rendering observation windows were 15.87 / 2.93 s.
Draw intervals measure DOM-observed completed draws/commits with interpolation,
not GPU-present timing or display FPS. The shorter GPU window and instrumentation
(observers, resource polling and one safe screenshot each) limit comparison.
Its worse rendering p95 is retained, not filtered away or retuned.

Active-only resource samples numbered 52 CPU and 9 CUDA. Service+worker RSS
median/p95 was 504/512 MB versus 1,403/1,403 MB; owned process CPU consumption
was 105/112% versus 89/91% of one CPU core. Browser RSS was approximately
1,198/1,218 MB versus 1,196/1,198 MB, and browser CPU was 42/53% versus 34/52%.
Whole-card VRAM used was 2,958/2,973 MiB versus 3,325/3,343 MiB; GPU utilization
was 90/92% versus 97/98%. These include the existing desktop applications; RSS
sums include shared pages. No unrelated applications were stopped to improve
the result. Server durations and browser durations each use their own clock;
no browser/Python clock subtraction was used.

Source sequences and observation hashes demonstrate that faster inference samples
different frames. Live trajectories therefore are not the fixed-input equivalence
test. No physics timestep or playback speed changed. Both safe screenshots were
opened and inspected: original Screen Gremlin over generated blocks/counter,
LIVE and SYNTHETIC SELECTED SOURCE labels, with no desktop imagery. No video or
OBS recording was made.

Missing GPU was tested twice: the dedicated tiny gate fails explicitly with
`CUDA_VISIBLE_DEVICES=''` (expected exit 1, one setup error, zero skips), and an
actual owned full-graph worker failed startup with zero new attempts, neutral
flight, closed capture, reaped process and released ownership. The subsequent
successful CUDA browser session exercised a fresh explicit start. Process fixture
faults cover initialization failure, OOM, hung/crashed worker, stale results,
Stop, source/lease loss and explicit restart. OOM is fault injection, not an
attempt to exhaust the user's GPU. No failure activates synthetic motion or CPU.

Executed validation and evidence (all paths under `artifacts/milestones/GPU01/`):

| Command/check | Exit and result | Evidence |
|---|---|---|
| `uv lock`; optional `uv sync ... --inexact`; `uv lock --check` | 0 | dependency/install logs |
| `make dependency-check` | 0; installed Python packages compatible, npm audit 0 vulnerabilities | dependency-check.log |
| `uv build --no-sources --out-dir artifacts/milestones/GPU01/build` | 0; source distribution and wheel built | python-build.log |
| `.venv/bin/python -m scripts.gpu01_validate prepare --output artifacts/milestones/GPU01/fixed-input` | 0, zero calls | fixed-input/plan.json |
| `timeout --signal=TERM --kill-after=5s 180s .venv/bin/python -m scripts.gpu01_validate execute --output artifacts/milestones/GPU01/fixed-input` | 0, 54 attempts | fixed-input/result.json, fixed-input-command.log |
| `.venv/bin/python -m scripts.gpu01_browser` | 0, 64 attempts | browser/execution.json, raw and clarified JSON |
| `.venv/bin/python -m pytest tests/gpu/test_exact.py -q --junitxml=artifacts/milestones/GPU01/exact-gpu-final.xml` | 0, 9 passed, 0 failed/skipped | exact-gpu-final.xml |
| `make verify-live LIVE_EVIDENCE=artifacts/milestones/GPU01/final-regression` | 0: 748 live Python, 351 live UI/contracts, 124 lab Python, 15 lab UI, 2 lab fixture browsers, 20 live fixture browsers; schemas/lint/build passed | verify-live.log, final-regression/ |
| `pytest tests/live/test_worker.py tests/live/test_recording.py tests/live/test_ground_recording.py -q`; `npm --prefix web test -- tests/Live.test.tsx`; web build | 0: 62 Python + 28 UI | wiring-audit-fixes.xml, wiring-audit-ui.xml |
| Final qualification/backend checks | 0: 10 passed | qualification-final.xml |
| `ruff check flytrap scripts tests`; `git diff --check` | 0 | final-checks evidence |

The initial recording-contract run had 9 failures out of 272 because adding an
optional provenance field changed historical canonical hashes. The reader now
preserves the original absent-field form, and the same 272 checks passed;
both XML reports remain. Initial dependency resolution failure and the expected
missing-device failure also remain. No failed full-graph inference occurred.

Accounting: started at **219/1,024**, added **118** (18 CPU fixed, 36 GPU fixed/
repeat, 32 CPU browser, 32 GPU browser), ended **337/1,024**, **687 remaining**.
GPU01 used **118/384**, leaving **266** of this task's ceiling unused. All
attempts were recorded before use as automated sessions. P00 remains **144**;
its ledger and all ten protected model/data/accounting files match the initial
hash snapshot. `final-integrity.json` confirms free model ownership. No ledger
was reset, no human session was used by agents, and no remote action occurred.

For manual A/B, run one at a time from `/home/kernel_sanders/dev/flycoinrh`:

```text
./scripts/dev_sg01_live.sh --backend cpu
./scripts/dev_sg01_live.sh --backend cuda
```

Both open the same frontend at `http://127.0.0.1:5173/live`. Stop the launcher
with Ctrl+C before switching. If an unrelated service occupies a port, use
`--api-port 8772 --ui-port 5174` and the matching URL. Startup stays idle;
the operator explicitly selects the approved OBS source and presses Start.
Server backend labels identify the implementation. OBS recording stays disabled.
Keep the same seed, scene and presentation for review; higher cadence still
samples different real-time frames. The next handoff is the operator's manual
CPU/GPU comparison and promotion decision, not another implementation milestone.
