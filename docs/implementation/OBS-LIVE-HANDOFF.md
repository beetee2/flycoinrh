# OBS live — local review handoff

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
