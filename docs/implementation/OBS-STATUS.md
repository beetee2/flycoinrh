# Active routing — Flyjam local OBS-to-flight

The 2026-09-15 assignment authorizes OBS00–OBS06, one numbered prompt per
instruction. The current execution is **OBS00 only**. It supersedes the P00-only
stop for this workstream. Historical navigation remains STOPPED; original 06
remains BLOCKED. P00 human product review is still PENDING. Public release,
external writes, tokens, paid services and privileged host changes are unauthorized.

| Milestone | Implementation | Next boundary |
|---|---|---|
| OBS00 | **PASS / COMPLETE** | Scope, executable contracts, idle app, host inspection |
| OBS01 | NOT_RUN | Explicitly selected OBS source, capture and encoding |
| OBS02 | NOT_RUN | Persistent model worker and independent call accounting |
| OBS03 | NOT_RUN | Decoder and authoritative fixed-step flight |
| OBS04 | NOT_RUN | Local control API, ownership, stream and replay storage |
| OBS05 | NOT_RUN | Interactive browser integration |
| OBS06 | NOT_RUN | Real validation, causal-control evidence, human review |

Current gates: real-model execution NOT_RUN; real-OBS BLOCKED (no registered video
device or selected source); causal-control NOT_RUN; human product review PENDING.
OBS automated full-model attempts: **0 / 1,024**, remaining **1,024**.
P00's separate ledger and historical results are preserved.

See [OBS00](milestones/OBS00.md) for actual commands, evidence and setup needs;
[live contracts and operating policy](OBS-CONTRACTS.md) for the frozen v1 foundation.
Next instruction: [01-capture.md](../../flyjam-obs-kit/prompts/01-capture.md).
Stop after OBS00; do not execute OBS01 in this turn.
