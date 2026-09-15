# OBS02 — persistent neural session and bounded lifecycle

2026-09-15. Starting checkout was clean at reviewed/pushed commit
`f0be7863abb86715916e37c7265287087c84820e`; remote main matched. No newer work
or existing FFmpeg repair was found. Executed the requested OBS01 prerequisite
repair, then read RESUME/SPEC/TEST_MATRIX and executed only OBS02.

## Prerequisite and evidence boundaries

OBS01's local hardware validation remains **PASS**. Its later hosted foundation
run failed because FFmpeg was absent: six failures, 2,657 passes; live checks
were skipped. The workflow now installs Ubuntu's official `ffmpeg` package and
logs its executable/version before tests. Repair checks passed locally and all
39 capture tests passed on clean Ubuntu 24.04, FFmpeg `7:6.1.1-3ubuntu5`.
See [OBS01's repair record](OBS01.md). **Hosted verification remains PENDING**:
the latest observed run is still [34979022968](https://github.com/beetee2/flycoinrh/actions/runs/34979022968).
No push or new hosted run occurred.

| Boundary | Result |
|---|---|
| OBS01 CI dependency repair / local and Ubuntu compatibility | **PASS** |
| Persistent worker, compiled mapping, accounting and lifecycle | **PASS / COMPLETE**, including integrated checks |
| Actual real-model gate with safe deterministic source | **PASS**, nine attempted calls |
| New desktop/OBS capture or recording | **NOT_RUN**, neither used |
| Whole-pipeline real OBS / flight / causal-control validation | **NOT_RUN**, later milestones |
| Human product review | **PENDING**, no approval inferred |

## Implementation

- `session.py`: explicit Start, unique session ID/generation, one reader and one
  persistent model process, capacity-one input selection, separate frame/step
  identities, one outstanding request, startup/step/session/lease deadlines,
  source/ownership loss and stale/foreign response rejection. Terminal sessions
  cannot restart. Fresh output is separate from historical measurements.
- `worker.py`, `neural.py`: bounded JSON over local `SOCK_SEQPACKET`; the actual
  controller receives only normalized Observation pixels. Load/reset once per
  session; original internal step seeds, 100 × 0.2 ms `windowed_reset`, immutable
  all-one gains and disabled learning. Response packets carry original pilot
  action, unmodified adapter output, raw motor rates, statistics and timings.
  Provenance is hashed once and retrieved separately from small snapshots.
- `sensory.py`: independently compiled raw-annotation sampling indices, checked
  against the historical P00 oracle during load. Per-step interception checks
  actual sensory drive and copies output without raw annotation reads or hashes.
  Diagnostic coverage arrays are available explicitly, outside live packets.
- `accounting.py`: acquire live-session then existing P00 flock, nonblocking.
  Pass the open descriptors to the worker and close without unlocking inherited
  ownership early. Append/fsync calls before inference; hash-chained rows plus a
  durable checkpoint reject corruption, missing/truncated records and exhaustion.
  Worker death after append remains charged and terminal counts are reconciled.
- `child.py` and capture cleanup: Linux parent-death signal installed before
  exec, with a parent-ID race check, for both the neural worker and FFmpeg.
  Stop reaps the neural child and confirms actual capture thread/child closure.
  Failed cleanup retains ownership until termination, preventing a second session
  from overlapping an unresolved reader. Stop returns within its configured bound.
- `scripts/live_real.py` / `make test-live-real`: fixed nine-call real validation,
  new evidence directory required, fixed ledger independent of output path,
  nonzero missing-data failure, and a 90-second process-group deadline. Recording
  is disabled; only safe generated input measurements are saved by this gate.

No historical controller, FlyEye, FlyBrain or checkpoint was edited. The browser
control API and flight decoder are subsequent milestones; the existing browser
continues to report its idle implementation capabilities accurately.

## Actual model validation

Command: `timeout --signal=TERM --kill-after=5s 90s make test-live-real
LIVE_REAL_EVIDENCE=artifacts/milestones/OBS02/real` (one command). **Exit 0**,
13.60 seconds including the make wrapper. The maintained make target now includes
that same outer timeout. `real.command.json`, `real.log`, and `real/result.json`
retain actual command identity and results.

Predeclared seed **20260915**; three continuous-source live steps, followed by
three untapped original-adapter calls and three historical-tap references using
those exact observations and seed progression. All nine were charged before
execution. There were no failures, replacement seeds or retries.

- Actual full graph: **165,122 neurons**; graph SHA256
  `4279e2222475b986a096634ea5f6ac9518d0f8feff3f3c2ed52ad1139d3cd2ed`.
- Existing baseline checkpoint SHA256:
  `adfa5cc48f476d99b39ac61779143f5f22e88f5940ebf0226a143c5585410ccc`.
- Safe `fixture-pattern` source; real model label remains distinct from source
  fixture label. Live session `a7430011c0334414945c42e58d54c5d2` admitted source
  sequences **132, 146, 160** at model steps **0, 1, 2**. Exact input bytes and
  paired responses are stored in `real/live-step-*.json`.
- **Three exact untapped output matches** and **three exact historical motor-rate
  and statistics matches**. Actual-data compiled mapping equals the independent
  annotation oracle. Instrumented model input opens during all live steps: **0**.
- Reader accepted **175 frames**, replacing **171**; three completed windows total
  **60 neural ms**. Observed average **2.15 model Hz** after readiness. Receipt-to-
  completion ages were **468.2, 469.9, 462.7 ms**; zero stale results. These are
  local receipt timings, not OBS producer latency or a throughput guarantee.
- All ten protected graph/model/checkpoint/P00 files checked by the gate matched
  before/after. P00 retains **144 attempts**, SHA256
  `3c4df0721f7f2d1b50494bd611d425a82e45aa0c61a344a14e54fce220e7747f`.

OBS automated ledger: **9 / 1,024 attempted; 1,015 remaining**, at
`artifacts/live/validation/attempts.jsonl`. Separate per-session ledgers identify
the live, untapped and historical reference calls. No human-session calls occurred.
Accounting failure blocks further work; deleting all accounting artifacts is
outside the protection of a local hash chain and must never be used to reset it.

The real gate preceded the final cleanup-confirmation hardening and test-module
rename. Its recorded per-file identity is preserved. Model, tap, encoder, worker,
configuration, dependencies and successful inference behavior remain identical;
the later change only checks already-stopped capture resources before releasing
ownership. Real parity evidence is reused; the changed failure path is covered
by actual process/thread regressions. No further neural calls were justified.

## Verification and recovery

Evidence: ignored `artifacts/milestones/OBS02/`. Test counts overlap; do not sum
them as unique tests. The final command runner records exact commands/exits and
JUnit reports under `final-reviewed/`. Final suites have zero failures, errors or
skips. Counts below overlap.

| Actual command | Result |
|---|---|
| `.venv/bin/python -m pytest tests/live/test_capture.py -q --junitxml=artifacts/milestones/OBS02/final-reviewed/capture.xml` | Exit 0; **39 passed** |
| `make verify test-upstream EVIDENCE=artifacts/milestones/OBS02/final-reviewed/foundation` | Exit 0; **2,714 Python**, **150 upstream**, **89 web contracts**, **9 UI**, **2 browser** passes; lint/schema/build/dependencies passed |
| `make verify-live LIVE_EVIDENCE=artifacts/milestones/OBS02/final-reviewed/live` | Exit 0; **332 live Python**, **93 live UI/contracts**, **124 lab Python**, **15 lab UI**, **2 browser** passes; schema/lint/build passed |
| Clean Ubuntu 24.04 Docker capture tests on final source | Exit 0; **39 passed**, FFmpeg `7:6.1.1-3ubuntu5`; exact command/image/source identity in `ubuntu-final/` |
| Bounded `make test-live-real` command above | Exit 0; **9 real calls**, all required comparisons passed |

Final review found no unresolved critical OBS02 model/privacy/lifecycle issue.
No new UI was authored; browser regression evidence exercises the existing idle
desktop/mobile service. Full browser/model/flight validation remains later work.

Meaningful regressions cover load/reset counts with an instrumented actual tiny
adapter, original outputs/seed sequence, cached mapping and hot-path I/O, bounded
IPC, newest-only clock admission, ledger fsync/corruption/1,024-call exhaustion,
P00 contention, hangs/crashes, stale/foreign/future results, expired lease, source
loss, lock identity loss, explicit restart, parent death, and capture cleanup
that blocks or returns before resources actually stop. Missing real data produces
a **BLOCKED/nonzero** gate rather than a synthetic pass.

An initial full repository run exited 2 at collection because new
`tests/live/test_sensory.py` collided with existing `tests/lab/test_sensory.py`.
Renamed it to `test_live_sensory.py`; retained the failed run under `final/`.
Review also found and repaired fixture producer labeling, consumed-slot freshness,
post-append crash accounting and cleanup ownership gaps before final checks.
Existing Starlette/AnyIO deprecation and Playwright color warnings remain visible.

## Handoff

Retained selected OBS source: `/dev/video0`, **OBS Virtual Camera**, fixed scene
**FLYJAM_INPUT**, operator-selected monitor, **1920×1080 YUYV at 60/1 fps**,
v4l2loopback 0.15.4-2, `keep_format=0`. Its prior OBS01 hardware evidence is
historical validation, not new capture consent. This turn opened no desktop
source, changed no OBS configuration and performed no privileged workstation
changes. Recording stayed disabled.

The source identity record also verifies **217 protected source/historical
evidence files unchanged** from the repair baseline. The implementation kits,
LICENSE/NOTICE, prior evidence, graph/checkpoint and P00 accounting are retained.
No push, public deployment, paid service, token action or social post occurred.

Next milestone: **OBS03 — decoder and authoritative flight**, on a new invocation.
Stop after OBS02. Hosted verification and later full-pipeline/human gates remain
separate; no broader OBS workstream completion is claimed.
