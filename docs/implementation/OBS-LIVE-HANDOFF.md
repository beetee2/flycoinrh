# SG01 — Screen Gremlin candidate

The default is now **Screen Gremlin**; choose **Legacy** locally for comparison.
Your ground-contact confirmation is recorded as operator evidence. Your manual
OBS smoke test using the repaired live launcher also **PASSED**, confirmed at
revision `05dbb75744352e6767a1408af4874ebea6c9936e` (recorded 2026-09-16).
This confirms that the repaired live workflow works. It does not approve the
character, motion appeal, overall product or public release.
[SG01 report and final evidence](milestones/SG01.md).

Final checks PASS: 679 live Python, 305 live UI/contracts, 20 live fixture browsers,
10 SG01 browsers, plus lab regressions and build/schema/lint checks. Installed
RTX 3080 / Chrome measured 59.8 display draws/s with neural updates at zero during
the synthetic test. Review media are in `artifacts/milestones/SG01/review/`: the
10-second `movement.webm`, four character backgrounds, landscape/portrait,
portrait turn, Legacy comparison and performance JSON.

Launch-profile repair **PASS**: 727 live Python, 350 live UI/contracts and 20
live desktop/mobile browser tests, plus lab regressions and the dedicated SG01
proxy checks. All 155 protected identities and 3,801 historical evidence files
remained unchanged during agent validation, which made zero new full-model calls
and performed no desktop capture. These are historical agent results, separate
from your subsequent manual smoke confirmation.

Hosted CI **PASS** for `05dbb75744352e6767a1408af4874ebea6c9936e`:
[run 35132375273](https://github.com/beetee2/flycoinrh/actions/runs/35132375273)
is `completed` / `success`, verified 2026-09-16 at 18:14:22 UTC. The `foundation`
job and all 16 reported steps succeeded. This is the hosted result; the local
validation suite was not repeated for this documentation update.

Choose one launcher from `/home/kernel_sanders/dev/flycoinrh`:

```text
./scripts/dev_sg01.sh
./scripts/dev_sg01_live.sh
```

Both open the same Screen Gremlin frontend at **http://127.0.0.1:5173/live**.
Run one at a time. Neither selects a source, captures, or infers on startup or
reload. Stop the launcher with Ctrl+C before switching profiles.

- **Art review — capture-only demo and saved replays.** `dev_sg01.sh` uses the
  dedicated safe API on 8770. The page labels this profile and disables Start,
  model-call/seed inputs and recording, with an explanation before a click.
  Load/Play synthetic preview is the existing 12-second movement demonstration.
  Live source → explicitly select the synthetic source → Preview source exercises
  capture-only display; Stop clears it. This service cannot perform inference.
  Recorded playback retains the read-only safe recording
  `8d4d624e6f4a4d3f8a9a7dbdc26d3d62`; original color footage remains absent.
- **Live flight.** `dev_sg01_live.sh` uses the normal live API on 8767 with
  server-controlled **human** execution purpose, normal device metadata and the
  existing neural-session factory. Explicitly select your approved OBS source,
  Preview if desired, then Start for manual use. OBS recording stays
  disabled. Start still requires ready graphics and respects existing ownership,
  session limits and accounting. A synthetic source on the ordinary
  `--safe-source` API remains inference-capable; source type is independent of
  the server's inference capability.

The launchers refuse occupied API or frontend ports, including an older service
on 8767. They never reuse that service or stop its owner. Stop your old launcher
explicitly, or select free ports, for example:
`./scripts/dev_sg01_live.sh --api-port 8772 --ui-port 5174`, then open
`http://127.0.0.1:5174/live`. The proxy target follows the chosen API port and
preserves Host/Origin checks. Ctrl+C and startup failure clean up only this
launcher's child processes.

API errors show fixed, validated guidance and stable codes. If the service cannot
confirm its capabilities, controls stay disabled; check the launcher and reload.
After connection/source loss, use the explanation, correct the source, and Start
explicitly. No automatic recovery starts capture or inference.

SG01 real OBS smoke is **PASS / operator-confirmed**, and remains **NOT_RUN by
the repair agent**. The manual smoke is complete. The focused
[launch-profile repair report](milestones/SG01.md#launch-profile-and-unavailable-control-repair)
records fixture tests and metadata-only checks separately from prior evidence.

The repair agent reported capture and inference stopped at its handoff; current
service state and model accounting were not rechecked for this documentation
update. No new model calls, desktop capture, recording, application changes, push
or milestone were performed. Character, motion appeal and overall product review
remain pending; public release remains unapproved. Stop after this update.
Older handoffs remain historical below.

---

# Ground-contact repair — human re-review

**Focused repair PASS; final product approval awaits your review.** Your
CHANGES_REQUESTED decision for ground penetration is preserved. The original
OBS06 technical and causal results remain accepted as recorded. Read the
[ground-repair report](milestones/OBS06-ground.md) and [flight rule](OBS-FLIGHT.md).

Open **http://127.0.0.1:8769/live**, press **Load synthetic preview**, then
**Play synthetic preview**. This dedicated service has no available capture or
inference sources. The 12-second sequence descends to contact around 2.64 seconds,
continues moving and turning horizontally, then departs after the upward command
at 8 seconds. Inspect ground clearance and camera framing, then try Pause, Stop
and Reset. It makes **zero neural calls** and is labeled SYNTHETIC CONTROL REPLAY.

Restart command, from the repository:
`.venv/bin/python -m scripts.live_ground_preview --port 8769`.
The built web assets are current; rebuild after future source edits with
`npm --prefix web run build`.

New physics is **flight-fixed20-ground-v2**, environment **flat-ground-v1**,
ground **z=-4**, clearance **1.5**, minimum fly-root altitude **-2.5**. A Ground
contact indicator explains constrained movement. The conservative proxy can leave
a small gap between feet and floor at some pitches. Existing decorative cones
have no collision. Historical v1 replays retain their original paths, including
below-ground motion. This repair does not redefine their physics or hashes.

The manual service at **http://127.0.0.1:8767/live** has been started with the
updated code and its existing human execution policy; it has no current session.
Capture/inference are stopped and OBS recording is disabled. No new real model
or OBS run was performed. Automated accounting is unchanged at **219/1,024**, with
**805 remaining**; P00 is **144**. All existing recording, ledger and protected
model identities checked unchanged.

Local regression passed: **3,031 repository Python**, **150 upstream**, **649 live
Python**, **242 live UI/contracts**, and **20 live desktop/mobile browser tests**,
plus foundation/lab checks. All six descent/contact/departure screenshots were
opened and inspected. The report records failures during development and an
older default JUnit file that may have been overwritten by one initial test run.

The [hosted workflow for reviewed revision 3ee5b72](https://github.com/beetee2/flycoinrh/actions/runs/35005380470)
finished **FAILURE** with two mobile browser failures. This local repair has not
been committed, pushed or tested remotely. **Stop for human review.** No further
model, GPU, learning, milestone, capture or remote action is authorized.

---

# Historical OBS06 handoff (superseded above)

**OBS06 technical validation passed. Capture and inference are off.**
Final product and causal-response approval remain yours.

| Status | Result |
|---|---|
| Implementation | PASS |
| Actual CPU model | PASS |
| Approved actual OBS source/lifecycle | PASS |
| Controlled input-influence diagnostic | PASS for the fixed safe stimuli |
| Ordinary OBS visual influence | INCONCLUSIVE |
| Human review | Start/Stop and updating inferred input confirmed; final product/causal approval PENDING |

You reported that switching videos to static content updated the exact inferred
input appropriately and Start/Stop seemed correct. You could not clearly tell
whether the flight path changed. No stronger visual response or unreported manual
check is inferred. [Full report](milestones/OBS06.md).

## Open the local app

The existing manual service is at **http://127.0.0.1:8767/live**, with
server-controlled **human** execution purpose. Page load does not capture or infer.
If that service has been stopped, the existing manual-use command is:

```text
.venv/bin/python -m flytrap.live serve --port 8767 --execution-purpose human
```

Run from `/home/kernel_sanders/dev/flycoinrh`. If the port belongs to another
service, use a free port and its matching URL. Human sessions require your explicit
Start and retain their own usage records and 120-second/512-call session bounds.
Agents must use `--execution-purpose automated`; the browser cannot change policy.
`make serve-live` retains automated accounting by default. Previously charged
manual sessions remain charged: current automated total is **219/1,024**, **805
remaining**, and P00 remains **144**.

## Source and review steps

Selected device: **/dev/video0**, source **v4l2-video0**, **OBS Virtual Camera**,
v4l2loopback, **1920×1080 YUYV at 60 fps**, `keep_format=0`. Keep **FLYJAM_INPUT**
selected, use safe content, and exclude Flyjam output. No automatic fallback is
allowed. `make live-devices` inspects metadata; `make live-doctor` checks runtime.
Selected-device inspection: `.venv/bin/python -m flytrap.live inspect-source --source v4l2-video0`.

1. Open `/live`, check **Graphics: Ready**, choose **Live source** and the approved
   source. **Preview source** captures temporarily without neural calls.
2. Keep OBS recording disabled. Use **Inspect input** to distinguish the newest
   source from the exact input attached to the latest inferred response.
3. Choose a short duration/call limit and press **Start live flight**. Capture,
   neural and rendering rates are different measurements. Judge motion, framing,
   and responsiveness yourself; changing input is not a promise of dramatic turns.
4. **Stop session** freezes travel. Source loss, hidden/closed control tab, transport
   loss and graphics failure also stop ownership. Recovery needs explicit Start.
5. For safe playback, choose **Recorded playback**, refresh and load
   `8d4d624e6f4a4d3f8a9a7dbdc26d3d62`. This is the two-call real CPU recording of
   deterministic generated imagery. Play/Pause/seek/download perform no inference.

OBS/monitor recording stays disabled by the server guard. The previously approved
two OBS05 processed inputs remain private historical evidence. This milestone saved
no additional screen inputs. Any future additional screen-input saving needs your
explicit approval.

## What the validation established

Actual changed content altered **143/256** processed pixels. Manually stopping
Virtual Camera caused `source_lost` and frozen flight; restart did not resume
inference. An explicit Start recovered. The final preview tab-closure check used
actual capture and zero model calls. Safe recording/replay, worker faults, stale
results, leases, shared locks, slow consumption, cleanup and regression passed.

The frozen comparison used one seed, eight safe stimuli and 32 calls. Changing
versus frozen input changed **37/56 motor-rate values**, decoded controls, and
the fixed four-second trajectory (final separation **9.172 world units**). Exact
repeat matched; actual zero sensory drive produced zero controls and translation.
These high-contrast diagnostic results do not settle everyday OBS responsiveness.
The model, encoder, decoder, renderer, CPU/reset semantics and learning-disabled
baseline remain unchanged.

Model identity: `baseline-8892b6e9ed06dc2c46d746be`; graph SHA256
`4279e2222475b986a096634ea5f6ac9518d0f8feff3f3c2ed52ad1139d3cd2ed`.
Encoder: `obs-rgb-letterbox16-v1`; decoder: `motor-flight-v1`; physics:
`flight-fixed20-v1`. Full source/configuration/runtime hashes are in private evidence.

The reviewed pushed revision `a9688b39caaebb71a0c1058a6bf923ef86aab314` has a
[successful hosted workflow](https://github.com/beetee2/flycoinrh/actions/runs/35000589668).
New OBS06 changes have passing local checks and remain uncommitted/unpushed.

## Private review material and recovery

Safe bundle: `artifacts/milestones/OBS06/review-bundle.zip`. It includes screenshots,
a short original-time browser replay video of safe real-model flight, causal
comparison, and validation summaries. It contains no private OBS preview or footage.
The video includes model startup time and only a short movement interval; it is not
a performance or broad responsiveness demonstration.

If a session fails, use Stop and check the source metadata and terminal reason.
Correct the source yourself, then explicitly Start. A graphics failure offers
bounded **Retry graphics** and stays paused. Do not reset/delete ledgers to recover
allowance, kill an unrelated service, or change device/kernel settings to force a
gate. Validation services on 8877/8878 are stopped at handoff.

Revalidation commands are recorded in [OBS06](milestones/OBS06.md). Actual-source
reruns require fresh source/content confirmation and coordinated producer actions.
The next step is your final local product and causal-response review.
