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
