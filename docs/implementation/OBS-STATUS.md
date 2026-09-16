# Active routing — ground repair complete; human re-review

**Ground repair implementation PASS. Product approval remains withheld pending
human re-review.** The operator requested changes for below-ground travel at
`3ee5b7247f2e4525bea60cb8fa3e3e260b33db8c`. Read the
[focused report](milestones/OBS06-ground.md), [handoff](OBS-LIVE-HANDOFF.md), and
[versioned flight rule](OBS-FLIGHT.md).

New sessions use **flight-fixed20-ground-v2 / flat-ground-v1**, floor z=-4 and
clearance 1.5. Old v1 replay paths, hashes and causal results remain unchanged.
Zero new full-connectome calls or desktop capture. Capture/inference are off;
OBS recording remains disabled. Ledgers remain **219/1,024 (805 remaining)** and
P00 **144**. No model/checkpoint or learning change.

Local aggregates PASS: 3,031 repository Python, 150 upstream, 649 live Python,
242 live UI/contracts, 20 live fixture browser tests, and required foundation/lab
checks. Desktop/mobile descent/contact/departure screenshots were inspected.
The reviewed revision's [hosted workflow](https://github.com/beetee2/flycoinrh/actions/runs/35005380470)
finished **FAILURE** (two mobile browser tests). This repair is local/uncommitted.

Zero-call preview: **http://127.0.0.1:8769/live** → Load → Play. The dedicated
preview has no capture/inference sources. Manual service 8767 has updated code
and is idle. **Stop for review; no additional milestone or experiment.**
Original OBS06 real-model/OBS/causal technical results remain accepted as recorded.

---

# Historical routing — OBS06 technical validation complete

**Technical gates PASS. Return for final human review.** Read
[OBS-LIVE-HANDOFF](OBS-LIVE-HANDOFF.md) and the [OBS06 report](milestones/OBS06.md).

| Status | Current result |
|---|---|
| implementation_status | PASS — regression, lifecycle, CI integration |
| real_model_status | PASS — CPU reference, browser, safe recording/replay |
| real_obs_status | PASS — approved source, changed input, actual producer stop/restart, preview tab closure |
| causal_validation_status | PASS for fixed safe-stimulus diagnostic; ordinary OBS visual influence INCONCLUSIVE |
| human_review | Start/Stop and inferred-input updates confirmed; final product and causal-response approval PENDING |

The operator reported exact inferred-input updates when switching videos to static
content, correctly behaving Start/Stop controls, and uncertainty about flight-path
changes. Unreported manual checks are not approved. Historical OBS03 synthetic
appearance approval remains separate.

[Hosted workflow 35000589668](https://github.com/beetee2/flycoinrh/actions/runs/35000589668)
is confirmed completed/success for reviewed revision
`a9688b39caaebb71a0c1058a6bf923ef86aab314`. OBS05 now has an appended handoff
update. OBS06 changes are local/uncommitted; no new hosted validation or push.

Actual OBS content change altered 143/256 pixels, compared in memory. Recording
and additional input saving remained off. Producer stop froze flight; producer
restart required explicit Start. Causal comparison used 32 calls: rates, controls,
and trajectories differed for predefined safe stimuli; exact repeat matched;
actually disconnected drive remained neutral. This does not establish strong
ordinary OBS responsiveness or human product approval.

Final accounting: **219/1,024, 805 remaining; P00 144 unchanged**. OBS06 began
at the actual 142 and added 77; every earlier automated-policy charge is preserved.
Human manual use: `.venv/bin/python -m flytrap.live serve --port 8767 --execution-purpose human`.
Agent runs use automated policy and the same durable remaining allowance.

Capture/inference are off. Existing human service: http://127.0.0.1:8767/live.
Safe review bundle: `artifacts/milestones/OBS06/review-bundle.zip`.
**Stop for final human review.** No further model/mapping experiment or remote work
is authorized. Previous routing below remains historical evidence.

---

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
