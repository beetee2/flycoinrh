# Active routing — Flyjam local OBS-to-flight

The 2026-09-15 assignment authorizes OBS00–OBS06, one numbered prompt per
instruction. The current execution is **OBS01 only**, now complete for independent
implementation and fixtures. It supersedes the P00-only
stop for this workstream. Historical navigation remains STOPPED; original 06
remains BLOCKED. P00 human product review is still PENDING. Public release,
external writes, tokens, paid services and privileged host changes are unauthorized.

| Milestone | Implementation | Next boundary |
|---|---|---|
| OBS00 | **PASS / COMPLETE** | Scope, executable contracts, idle app, host inspection |
| OBS01 | **PASS / COMPLETE** | Fixtures, selected real preview, producer stop/restart and patterned-source checks **PASS** |
| OBS02 | NOT_RUN | Persistent model worker and independent call accounting |
| OBS03 | NOT_RUN | Decoder and authoritative fixed-step flight |
| OBS04 | NOT_RUN | Local control API, ownership, stream and replay storage |
| OBS05 | NOT_RUN | Interactive browser integration |
| OBS06 | NOT_RUN | Real validation, causal-control evidence, human review |

Current gates: real-model execution NOT_RUN; whole-pipeline real-OBS gate remains
OBS06. The operator explicitly selected `/dev/video0`, **OBS Virtual Camera**,
fixed scene `FLYJAM_INPUT`, monitor capture. Identity, 1920×1080 YUYV/60 fps,
bounded real preview, browser rendering, producer stop and fresh restart passed.
Driver status uses exclusive capabilities with `keep_format=0`; loss was detected
about 61 ms after the observed driver transition. The real patterned-source
color/orientation/counter check passed after diagnostic corrections. Capture is
closed; the operator-restarted OBS instance remains under operator control.
Causal-control NOT_RUN; human product review PENDING.
OBS automated full-model attempts: **0 / 1,024**, remaining **1,024**.
P00's separate ledger and historical results are preserved.

See [OBS01](milestones/OBS01.md) for actual commands, evidence and setup needs;
[live contracts and operating policy](OBS-CONTRACTS.md) for the frozen v1 foundation.
Next invocation selects [02-neural-session.md](../../flyjam-obs-kit/prompts/02-neural-session.md)
using the explicitly labeled fixture source or the currently approved source within
the next milestone's authority and bounds.
Per RESUME, a device permission block does not block independent OBS02–OBS05 code.
Stop after OBS01; OBS02 has not been executed.
