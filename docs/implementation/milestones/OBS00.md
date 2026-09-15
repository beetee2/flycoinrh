# OBS00 — scope, executable contracts and environment

Date: 2026-09-15 US/Central. Initial HEAD:
`1d120236b4ed21f9c9e531699b97a3b3389ab2cf`; initial working tree clean.
The checkout is newer than the kit's reviewed `a1af684` and was preserved.

implementation: **PASS / COMPLETE**
real_model_execution: **NOT_RUN**
real_OBS: **BLOCKED — no registered video device or selected source**
causal_control: **NOT_RUN**
human_product_review: **PENDING — no answers supplied**
automated_model_attempts: **0 / 1,024; 1,024 remaining**

## Authority and scope

Executed only [prompt 00](../../../flyjam-obs-kit/prompts/00-scope-and-contracts.md).
Read AGENTS, the new SPEC/TEST_MATRIX, historical PLAN/BOUNDARIES, STATUS/PIVOT/P00
and the actual controller, lab runner/sensory/API/budget, web entry, Makefile and
workflow. The current explicit assignment supersedes the stop in
[PIVOT, “Suggested later outline”](../PIVOT.md) and the historical STATUS P00 routing
for OBS00–OBS06 only. No further approval gate was inferred. The active routing
note and [OBS-STATUS](../OBS-STATUS.md) preserve historical navigation/P00 outcomes.
Original 06 stays blocked; P00 human product review stays pending.

## Delivered

- `flytrap/live/contracts.py`: twelve versioned top-level contracts covering source
  capability, frame/timing, encoder, neural sample, flight controls/state,
  session/config/status, stream, replay, health and app config. Strict types,
  lengths, safe numeric bounds, finite values, literal types and unknown-field
  rejection. Semantic checks cover producer clock availability, response/expiry
  ordering, real/fixture backend consistency, matching source/session/generation,
  replay consent, source/config binding and recording size.
- Generated JSON Schema, TypeScript and shared wire corpus; strict browser AJV
  parsing mirrors nested semantic checks. Seventy-nine shared positive/negative
  cases include explicitly synthetic inputs and real-metadata shape only. A real
  label is not evidence that a real gate ran. `make check-live-generated` checks
  Python schema/corpus and TypeScript drift.
- `environment.py` and the module CLI: sysfs-only device discovery, bounded metadata
  subprocesses, runtime/tool/disk inspection and checksum-based raw/model/source
  identity checks. Never opens device nodes or loads/calls the model. Unknown
  formats/capabilities are null. Output states that real-OBS has not run. Missing
  prerequisites and existing evidence-file conflicts fail nonzero.
- `api.py` and `web/src/live/`: loopback idle app, trusted hosts, private responses,
  approved built assets only, health/config GETs and clear unavailable capture/
  inference status. No mutation endpoint exists in OBS00. Opening/reloading the
  page does only health/config reads. The existing `/lab` route is retained.
- Actual `live-devices`, `live-doctor`, `serve-live`, generation, fast test and
  verification Make targets. A maintained desktop/mobile browser test catches
  startup/runtime errors against the actual built UI and service. CI adds
  `verify-live` with a synthetic-report-only evidence directory; no hosted run or
  external write was performed.
- [OBS-CONTRACTS](../OBS-CONTRACTS.md) freezes the encoder math and interface
  ceilings, documents bounds, clocks/freshness, consent, ownership/shared P00
  lock reuse, separate 1,024-call accounting, private artifacts and acceptance
  states. Persistent worker lifetime preserves unchanged `windowed_reset`
  numerical dynamics, gains and seed progression. Execution belongs to OBS02.

No dependencies, lockfiles, model files, checkpoint semantics or P00 ledger changed.
Capture/inference/decoder/physics/session/replay execution remain their numbered
deliverables; OBS00 does not claim those boundaries pass.

## Environment and exact setup needs

Actual host inspection: Arch Linux, kernel `7.2.4-arch1-2`, x86_64;
Python 3.14.7, Node 26.8.2, npm 12.0.2. Installed packages include FastAPI 0.128.0,
Pydantic 2.13.5, Uvicorn 0.40.0, NumPy 2.4.2, SciPy 1.17.1, pandas 3.0.1,
PyArrow 23.0.1 and Pillow 12.2.0. Initial free disk: 664,278,638,592 bytes.

Selected backend: **FFmpeg n9.0.1 V4L2 subprocess**. Installed `ffmpeg -devices`
advertises `video4linux2,v4l2`; `ffmpeg -h demuxer=v4l2` confirms supported options.
The bounded subprocess approach needs no additional Python dependency.
`v4l2-ctl 1.32.0` and OBS 32.2.2 are present. Actual output and tool exit codes are
in `environment/doctor.json` and the final `doctor-target.log`.

Full raw files, graph, source-bound checkpoint and protected model source hashes
match. Graph SHA256:
`4279e2222475b986a096634ea5f6ac9518d0f8feff3f3c2ed52ad1139d3cd2ed`.
This is byte-identity evidence, not model execution evidence.

Host blockers and next operator steps:

1. No `/sys/class/video4linux` class or `/dev/video*` source is available;
   v4l2loopback is not loaded. The operator must provide/configure an OBS virtual
   device. No installation, permission change, module load or sudo was performed.
   Privileged setup requires explicit authorization.
2. The operator must explicitly select the source before opening it for any
   ioctl inspection, preview or capture. OBS00 stores no selection. Metadata
   discovery alone never chooses a webcam or virtual device.
3. After selection, OBS01 must validate resolved character-device/driver identity,
   formats/color assumptions and installed producer-stop behavior. Driver or
   authenticated read-only OBS status signaling must support verified freshness;
   duplication/static/black frames cannot be treated as proof of producer health.

Independent OBS01 implementation can proceed on its next numbered instruction;
missing hardware blocks its real hardware gate. No broad product reapproval is
required to implement OBS01 under the current workstream authorization.

## Executed validation and evidence

All paths below are under ignored
[`artifacts/milestones/OBS00/`](../../../artifacts/milestones/OBS00/).
Commands, exits and raw logs are retained. Counts overlap across runs and must
not be summed as unique tests. Every passing suite below has zero failures,
errors and skips.

| Actual command | Result | Evidence |
|---|---|---|
| `make verify-live LIVE_EVIDENCE=artifacts/milestones/OBS00/complete` | Exit 0: 109 live Python, 93 live UI/contracts, 124 lab Python, 15 lab UI, 2 actual idle-service browser passes; generated checks, Ruff, TypeScript/build PASS | `complete.command.json`, `complete.log`, `complete/*.xml`, `complete/browser/report.json` |
| `make verify test-upstream EVIDENCE=artifacts/milestones/OBS00/repository` | Exit 0: 2,484 Python, 150 upstream, 89 historical web contracts, 9 historical UI, 2 historical fixture browser; doctor/generated/lint/build/dependency checks PASS | `repository.command.json`, `repository.log`, `repository/` |
| `make live-devices` | Exit 2, BLOCKED: no registered video devices; capture false | `devices-target.command.json`, `.log` |
| `make live-doctor` | Exit 2, BLOCKED: device prerequisite missing; model/data/source hashes and FFmpeg support OK; zero neural calls | `doctor-target.command.json`, `.log`, `environment/doctor.json` |
| `.venv/bin/python -m flytrap.live --help` | Exit 0, actual commands/help | `live-help.command.json`, `.log` |
| `make serve-live`, HTTP reads, then owned-process shutdown | `/health/live`, `/api/live/config`, `/live` all HTTP 200 at default port 8767; idle flags correct. Intentional SIGTERM shutdown, make exit −15; no server left running | `serve-complete.command.json`, `.log` |
| Preservation / source identity | 261 prior file hashes checked, 257 identical; only four intentional integration files changed | `preservation-before.json`, `preservation-after.json`, `source-identity.json` |

The broad repository run preceded the final live-only source/label checks and CSP
repair. The final `verify-live` reran all affected live/lab contracts, APIs, UI,
generated checks, lint, types/build and both new browser cases after those changes.
Unchanged historical checks were not needlessly rerun. No full-model test or P00
real-browser comparison was run. Hosted CI is unexecuted.

Earlier evidence is retained: the initial targeted Python run had 83 passes;
initial integrated live verification had 102 Python and 86 UI/contract passes.
Agent environment/web command ledgers and logs are in `environment/` and `web/`.
The final shared corpus has 79 cases; Python adds nonfinite/type/API/metadata
checks and the browser suite adds parser and component checks.

Resolved development failures:

- Initial web types check found two AJV cast errors; corrected before build.
- An ad hoc browser probe timed out after 30 seconds. A bounded diagnostic then
  reproduced CSP blocking AJV's bundled-schema compiler. The header now permits
  that compiler while restricting scripts/resources to the local origin;
  client-supplied schemas/code are not accepted. Both maintained real-service
  browser cases pass after repair. Failed logs are `browser-smoke.log`,
  `initial-browser-timeout.json`, and `browser-diagnostic.*`.
- The first expanded corpus run had 108 passes/1 failure because a template
  shared the latest-frame and neural-frame Python object. JSON cloning now breaks
  those aliases, correctly testing different source IDs; final 109/109 passes.
  Failed evidence remains in `verified.*` and `verified/`.
- Existing Starlette/AnyIO deprecation and Playwright color-environment warnings
  remain visible; they did not fail checks.

## Preservation, visual review and handoff

Only `.github/workflows/foundation.yml`, Makefile, STATUS and `web/src/main.tsx`
changed among the 261 previously hashed files. Historical implementation kits,
LICENSE/NOTICE, model/controller source, lockfiles, configurations, checkpoint
and P00 call ledger match their original hashes. All new implementation/report
files are additive. Source identity records actual HEAD, file hashes and working
diff; no commit, push, PR, public service or external write was performed.
The actual P00 ledger currently contains **144 attempts**, unchanged during OBS00;
the historical P00 report's 72-attempt count is an older snapshot. OBS00 consumed
zero attempts from either allowance.

Opened and inspected the actual desktop/mobile screenshots under
`complete/browser/results/`. The idle status, unavailable capture/inference
notice, explicit source-selection requirement and recording-off state are legible.
Desktop uses four facts columns; mobile wraps into two with no overlap or page
overflow. There is no rendered fly or motion claim in this foundation. This is an
engineering visual check, not human approval of the future flight experience.

Start with **`make serve-live`**, then open **http://127.0.0.1:8767/live**.
Use `LIVE_PORT=8877` if occupied; preserve unrelated listeners. Built assets are
present. Metadata commands can save fresh reports with `--evidence-dir`; test
targets accept `LIVE_EVIDENCE`. No operator shell script was needed.

**Stop here. Next handoff: [OBS01 — capture](../../../flyjam-obs-kit/prompts/01-capture.md).**
No OBS01 work or unselected source capture was performed.
