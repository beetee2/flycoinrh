# Active routing — OBS05 implemented; hands-on review next

**OBS05 implementation and required local validation PASS / COMPLETE.** Read the
[OBS05 report](milestones/OBS05.md) for controls, ownership, accounting, recording,
real-model and approved OBS evidence. OBS06 is not authorized by this invocation.

OBS03 repaired synthetic preview appearance/motion remains **APPROVED by the
operator**. Real neural-driven motion/framing/responsiveness is **PENDING human
review**. These approvals are separate.

Hosted workflow [34995107755](https://github.com/beetee2/flycoinrh/actions/runs/34995107755)
was checked and **PASS** for reviewed revision
`2bc0c675c62b5aeaaa5393697f02406d53a7b195`, including the scoped sandbox repair and
repository/live verification. The original failed workflow remains historical.
OBS05 changes are local; no push or hosted validation of these changes is claimed.

The CPU reference gate passed. The two-call real-model browser journey verified
input/neural/pose identities; its download signed-zero defect was repaired and the
same recording passed a zero-call replay/download browser check. A final complete
real-model Start/record/replay/download browser run then passed with two further
automated calls. Final live checks passed: 597 Python, 222 UI/contracts, 124 lab
Python, 15 lab UI and 18 desktop/mobile browser tests. Approved OBS
Preview/Stop and two real-model calls passed with recording off. Both saved OBS
16×16 inputs were identical, so changed-content responsiveness and current OBS
producer-stop behavior remain hands-on checks.

Actual accounting: **OBS 61/1,024, 963 remaining; P00 144 attempts unchanged**.
The service defaults to server-controlled automated accounting. Preview/replay
consume no calls. CPU/reset/seed/flight mapping and learning-disabled baseline
remain unchanged. Exactly two approved processed PNGs are private local evidence
at `artifacts/milestones/OBS05/actual-obs/approved-inputs/`.

Agent validation added 18 calls. A later independently started browser session
added 34 calls under the default automated policy and ended at its bound. The final
service resource check confirmed capture and inference stopped. No product approval
was inferred from that session.

Startup: **`make serve-live`**, **http://127.0.0.1:8767/live**. The handoff leaves
capture and inference stopped, recording disabled for OBS. See the report's short
checklist and local input viewer. **Stop after OBS05; wait for hands-on review.**

Earlier routing below remains historical and is superseded by this entry.

---

# Active routing — OBS04 complete; stop before OBS05

**OBS04 implementation and local validation PASS / COMPLETE.** Read
[OBS04](milestones/OBS04.md) for API contracts, ownership/lease handling, private
opt-in recording, verified replay, actual commands/counts and handoff.

The operator explicitly approved repaired-build playback and current
appearance/motion at `d07841cfe426c36e01c5c805a790d6448f420c64` after enabling
hardware acceleration. This is **operator confirmation**, not an independently
executed agent test. It resolves OBS03's repaired-build and human review gates;
the [appended approval](milestones/OBS03.md) preserves the original failure/repair.

| Gate | Current result |
|---|---|
| OBS03 repaired-build operator playback and appearance/motion | **APPROVED**, explicit operator confirmation |
| OBS04 local implementation and required validation | **PASS**: 583 live Python, 193 live UI/contracts, 124 lab Python, 15 lab UI, 8 browser tests; all required broad checks pass |
| Hosted run [34991210953](https://github.com/beetee2/flycoinrh/actions/runs/34991210953) at `d07841c` | **FAILURE**: Chromium sandbox startup denied by runner AppArmor |
| Scoped workflow prerequisite repair | **Local validation PASS; hosted rerun NOT_RUN**, no push/dispatch authorized |
| Real neural-driven browser flight / real OBS / desktop recording in OBS04 | **NOT_RUN**; synthetic fixtures cannot satisfy these gates |
| OBS05 / OBS06 / public release | **NOT_AUTHORIZED** by this instruction |

The actual API is available through `make serve-live` at
**http://127.0.0.1:8767/live**; it was left running idle and verified with HTTP
reads. The page keeps the approved synthetic stage; OBS05 owns complete operator
controls and renderer/replay wiring. Recording requires explicit consent on each
Start and remains off by default. No desktop recording or additional capture
consent was used. All storage checks used safe synthetic inputs and temporary files.

Actual ledgers remain **OBS 9/1,024 (1,015 remaining), P00 144 attempts**.
OBS04 added zero full-model calls. All 60 protected model/checkpoint, notice,
accounting and kit identities match prior evidence. CPU/reset/seed semantics,
encoder, decoder, renderer and learning-disabled baseline are preserved.

**Stop before OBS05.** A future authorized invocation may select
`flyjam-obs-kit/prompts/05-browser.md`. No remote push, public deployment, paid
service, token transaction or social post was performed. Historical navigation
remains STOPPED and original 06 remains BLOCKED.

The routing below is historical and superseded by this entry.

---

# Active routing — OBS03 browser repair

**OBS03 repair and automated checks PASS. Human review BLOCKED pending
review of the repaired build. Stop here; OBS04 is not authorized.** Read the [repair report](milestones/OBS03.md)
and [fixed mapping](OBS-FLIGHT.md). Reviewed pushed revision:
`58fbfd275821eb31c8a37df0cd55bde6e0a1676e`; repair remains local/uncommitted.

| Gate | Current status |
|---|---|
| Automated rendering tests | PASS: 8 desktop/mobile browser tests; live/lab UI 150, live Python 473, lab Python 124 PASS |
| Actual installed-browser compatibility | PASS: 4 headed scene tests in Chrome 153.0.8010.36; minimal/exact-attribute probes also PASS |
| Operator normal-browser playback | Prior preview PASS by operator confirmation after enabling acceleration; repaired build BLOCKED pending reload/retest |
| Human appearance/motion/framing approval | BLOCKED pending operator review; visible movement is not approval |
| OBS04–OBS06 | NOT_RUN; OBS04 remains unauthorized |

Normal Chrome now reports hardware WebGL on RTX 3080 / NVIDIA 610.57.04 via
ANGLE/OpenGL. Bundled Playwright 153.0.8010.12 headless uses SwiftShader.
Their evidence is separate. The original failure was not independently reproduced;
the successful operator setting change supports a browser-configuration cause.
No host change or driver/scene workaround is proposed.

The repaired preview separates **Graphics** and **Preview data**, preserves local
sanitized diagnostics, and offers **Retry graphics** (one attempt per click,
maximum three retries per page). Context loss freezes playback. Successful retry
recreates the last successful pose and stays paused until Play.

Review at **http://127.0.0.1:8767/live** after reloading. Confirm Graphics Ready,
then Load, Play, Pause, Stop and Reset, and review appearance/motion/framing.
The preview remains **SYNTHETIC CONTROL REPLAY**; real neural wiring is later work.
Evidence: `artifacts/milestones/OBS03/browser-repair/`. Prior OBS03 passes and
screenshots remain historical evidence, without implying normal-browser success.

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
