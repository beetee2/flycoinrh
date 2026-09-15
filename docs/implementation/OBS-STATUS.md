# Active routing — Flyjam local OBS-to-flight

**OBS03 PASS / COMPLETE. Stop after OBS03.** Next invocation may authorize
[OBS04 — API and replay](../../flyjam-obs-kit/prompts/04-api-and-replay.md).
Read the [OBS03 report](milestones/OBS03.md),
[fixed decoder/physics mapping](OBS-FLIGHT.md) and
[upstream review and deferred backports](OBS-UPSTREAM-REVIEW.md).

| Milestone | Implementation | Boundary |
|---|---|---|
| OBS00 | **PASS / COMPLETE** | Contracts, idle app, host inspection |
| OBS01 | **PASS / COMPLETE** | Selected real preview, producer stop/restart and patterned-source checks |
| OBS02 | **PASS / COMPLETE** | Persistent worker, independent accounting, safe-source real model |
| OBS03 | **PASS / COMPLETE** | Typed motor decoder, session-owned 20 ms flight, exact replay, synthetic 3D preview |
| OBS04 | NOT_RUN | Local control API, ownership, stream and consented replay storage |
| OBS05 | NOT_RUN | Interactive source/neural/browser integration |
| OBS06 | NOT_RUN | Real validation, causal-control evidence, human review |

## Current evidence

Hosted run [34982619140](https://github.com/beetee2/flycoinrh/actions/runs/34982619140)
was freshly verified **completed/success** for reviewed fork
`7c35af0299d918f6294e2ba64452ec89108372d8`. This resolves the previous pending
OBS01/OBS02 hosted prerequisite; new OBS03 changes are local and uncommitted.

Final checks: **2,855 Python**, **150 upstream**, **473 live Python**,
**125 live UI/contracts**, **124 lab Python**, **15 lab UI**, **4 live browser**
passes, plus foundation UI/browser/contracts, schemas, lint, build and dependency
checks. Counts overlap; final suites have zero failures/errors/skips. Actual
commands, counts, source identity, opened desktop/mobile screenshots and synthetic
payload are under ignored `artifacts/milestones/OBS03/`.

Preview service is idle at **http://127.0.0.1:8767/live**. Use **Load synthetic
preview**, then **Play synthetic preview**. Pause/Stop freeze travel; Reset returns
to the initial pose. The preview is explicitly **SYNTHETIC CONTROL REPLAY**.
[Desktop screenshot](../../artifacts/milestones/OBS03/preview-desktop.png) ·
[Mobile screenshot](../../artifacts/milestones/OBS03/preview-mobile.png).

The server flight decoder is integrated with the persistent neural session and
verified using synthetic subprocess responses. The browser currently consumes
only the fixed synthetic snapshot sequence. Real source-to-browser wiring,
consented durable replay storage and causal-control validation remain later work.
Human appearance/motion/framing/responsiveness review remains **PENDING**.

## Preserved baseline and consent

CPU, all-one gains, learning disabled, `windowed_reset`, 100 integration steps,
checkpoint, reset/seed semantics and sensory scope are preserved. GPU integration,
learning corrections and upstream state/sensory extensions remain separate work
as detailed in the upstream review. Original procedural geometry was used;
three.js 0.186.0 is locally bundled with its MIT notice. Repository attribution
and notices remain intact.

OBS automated full-model attempts stay **9 / 1,024**, **1,015 remaining**.
OBS03 made zero additional full-model calls. P00 remains at **144 attempts**.
The prior OBS02 safe-source real-model evidence remains historical **PASS**;
OBS03 makes no new real-model or real-OBS claim.

Selected source remains `/dev/video0`, **OBS Virtual Camera**, scene
**FLYJAM_INPUT**, 1920×1080 YUYV at 60 fps. OBS01 hardware checks remain historical
PASS. This milestone performed no new desktop capture or recording and extended
no capture consent. Model/protected/accounting file hashes match prior evidence.

No remote push, PR, public deployment, GPU activation, paid service, token action
or social post occurred. Historical navigation remains STOPPED, original 06
remains BLOCKED, and P00 human product review remains PENDING.
