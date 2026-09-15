# Active routing — Flyjam local OBS-to-flight

The 2026-09-15 assignment authorizes OBS00–OBS06, one numbered prompt per
instruction. The current execution repairs the **OBS01 CI prerequisite**, then
implements **OBS02 only**. The repair passed local repository/live checks and
all 39 capture tests on clean Ubuntu 24.04 with Ubuntu FFmpeg 6.1.1. Hosted
verification remains **PENDING**; the latest observed hosted run is the reported
failure at `f0be786`. Prior local OBS01 hardware validation remains **PASS**.
This work supersedes the P00-only
stop for this workstream. Historical navigation remains STOPPED; original 06
remains BLOCKED. P00 human product review is still PENDING. Public release,
external writes, tokens, paid services and privileged host changes are unauthorized.

| Milestone | Implementation | Next boundary |
|---|---|---|
| OBS00 | **PASS / COMPLETE** | Scope, executable contracts, idle app, host inspection |
| OBS01 | **PASS / COMPLETE** | Fixtures, selected real preview, producer stop/restart and patterned-source checks **PASS** |
| OBS02 | **PASS / COMPLETE** | Persistent worker, independent accounting, required checks and safe-source real model **PASS** |
| OBS03 | NOT_RUN | Decoder and authoritative fixed-step flight |
| OBS04 | NOT_RUN | Local control API, ownership, stream and replay storage |
| OBS05 | NOT_RUN | Interactive browser integration |
| OBS06 | NOT_RUN | Real validation, causal-control evidence, human review |

Current gates: OBS02 safe-source real-model execution **PASS**, nine calls;
whole-pipeline real-OBS gate remains OBS06. Previously, the operator explicitly selected `/dev/video0`, **OBS Virtual Camera**,
fixed scene `FLYJAM_INPUT`, monitor capture. Identity, 1920×1080 YUYV/60 fps,
bounded real preview, browser rendering, producer stop and fresh restart passed.
Driver status uses exclusive capabilities with `keep_format=0`; loss was detected
about 61 ms after the observed driver transition. The real patterned-source
color/orientation/counter check passed after diagnostic corrections. Capture is
closed; the operator-restarted OBS instance remains under operator control.
Causal-control NOT_RUN; human product review PENDING.
OBS automated full-model attempts: **9 / 1,024**, remaining **1,015**.
P00's separate ledger and historical results are preserved.

Local final checks: **2,714 Python**, **150 upstream**, **332 live Python**,
all required frontend/browser/schema/build/dependency checks passed. Clean Ubuntu
24.04 final source capture validation: **39 passed**. Counts overlap; zero test
failures/errors/skips in the final suites. Hosted repair verification is pending.

See [OBS01](milestones/OBS01.md) and [OBS02](milestones/OBS02.md) for commands and evidence;
[live contracts and operating policy](OBS-CONTRACTS.md) for the frozen v1 foundation.
Completed [02-neural-session.md](../../flyjam-obs-kit/prompts/02-neural-session.md).
Initial real-model validation used the safe deterministic `fixture-pattern`
source. Selected OBS identity is retained for handoff; capture consent is not extended.
Per RESUME, a device permission block does not block independent OBS02–OBS05 code.
Stop after OBS02. No recording or new desktop capture is authorized in this turn.
Next invocation selects **OBS03**, decoder and authoritative flight.
