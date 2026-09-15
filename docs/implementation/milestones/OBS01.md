# OBS01 — selected source, continuous capture and exact encoding

## CI prerequisite repair — 2026-09-15

The historical hardware results below remain completed local validation. A later
[hosted run 34979022968](https://github.com/beetee2/flycoinrh/actions/runs/34979022968)
for `f0be7863abb86715916e37c7265287087c84820e` failed in job `104414146212`:
`make verify test-upstream` reached **2,657 passed / six failed**, all six actual
FFmpeg capture tests raising `FileNotFoundError: ffmpeg`. The live workflow step
was skipped. Initial repair inspection found a clean checkout and remote main at
that same commit, with no newer run or existing dependency fix.

`.github/workflows/foundation.yml` now installs `ffmpeg` using Ubuntu's official
apt repositories on the existing Ubuntu 24.04 runner, before bootstrap/test steps,
and logs `command -v ffmpeg` plus `ffmpeg -version`. Actual FFmpeg integration
tests remain required. Repair evidence is under
`artifacts/milestones/OBS01/ci-repair/`; it is separate from historical hardware
evidence. Local verification is **PASS**: 39 capture tests;
`make verify test-upstream` (2,663 Python, 150 upstream, 89 web contracts,
nine UI and two browser passes); `make verify-live` (281 live Python, 93 live
UI/contracts, 124 lab Python, 15 lab UI and two idle-browser passes).
All three commands exited 0; test failures/errors/skips were zero. Schema checks,
lint, builds and dependency checks passed. Commands, exits, logs and JUnit counts
are in `ci-repair/local/`. This uses local Arch FFmpeg `n9.0.1`.
Clean-Ubuntu compatibility validation is **PASS**: all 39 capture tests passed
(zero failures/errors/skips), container command exit 0, official Ubuntu 24.04
image digest `sha256:224a1869083a311ef3f13648a154ba79832fbef6364d31493642ca03082da254`.
Ubuntu's signed noble/universe package `7:6.1.1-3ubuntu5` provides FFmpeg 6.1.1
at `/usr/bin/ffmpeg`. Actual tests exercised `nullsrc`/`geq`, BT.601 `scale`,
RGB24/BGR24/YUYV422/NV12, PPM/image2pipe and passthrough/flushed timing. Installed
help confirmed V4L2 input and buffering/timing options without opening a device.
See `ci-repair/ubuntu/compatibility.md` for exact environment differences and logs.
No OBS or kernel devices were installed. Hosted verification
of this repair is **PENDING**; no push or hosted execution is authorized here.
This repair uses zero neural calls and performs no desktop capture or OBS changes.

## Historical OBS01 execution

Date: 2026-09-15 US/Central. Initial HEAD `2a170a7` (OBS00); initial tree clean.
Executed only [OBS01](../../../flyjam-obs-kit/prompts/01-capture.md), using the
current [resume policy](../../../flyjam-obs-kit/RESUME.md).

| Boundary | Result |
|---|---|
| Independent implementation / fixture checks | **PASS / COMPLETE** |
| Approved real-device identity and bounded preview | **PASS** |
| Actual producer stop, cleanup, explicit restart | **PASS** |
| Real browser preview, matched encoded input, automatic expiry | **PASS** |
| Real-source known color/orientation and visible counter | **PASS**, after bounded diagnostic repair |
| Real model / whole-pipeline OBS / causal control | **NOT_RUN**, later milestones |
| Human product review | **PENDING**, no taste approval inferred |

Zero neural calls. OBS automated allowance remains **0 / 1,024; 1,024 remaining**.
P00's separate 144-attempt ledger is preserved. Recording remained disabled.

## Delivered

- `device.py`: explicit `v4l2-videoN` selection, canonical character-device and
  permissions checks, bounded helper process for read-only V4L2 ioctls, driver/
  capability/format/stride/dimensions/rate/color validation and identity checks.
  Accepts progressive packed RGB3/BGR3/YUYV/NV12 at 1–60 fps, ≤8192 per dimension
  and ≤32 MiB decoded RGB. Unsupported formats fail without another device fallback.
- `capture.py`: continuously drained FFmpeg PPM output, capacity-one latest slot,
  epochs/sequences/receipt timestamps, replacement/rejection counts, bounded partial
  reads/EOF/hangs/diagnostics, format watcher, stop/kill/reap and preview expiry.
  Confirmed device configuration can be pinned before starting capture.
- `producer.py` plus driver checks: authenticated read-only OBS v5 monitor with
  bounded localhost polling and heartbeat expiry. The installed driver instead
  supports exclusive capture/output capabilities with `keep_format=0`; this is
  checked repeatedly. Static/repeated/black frames never determine producer health.
- `encoding.py`: immutable RGB envelope, exact frozen integer letterbox16 encoder,
  uint8 bytes and SHA256 retained beside a fresh normalized Observation. Preview
  source thumbnails and exact encoded inputs carry the same identity.
- `fixture.py` and `assets/obs-test.html`: explicitly labeled deterministic indexed
  synthetic frames and an original moving-shape/counter/color-marker page.
- `preview.py` and CLI: explicit preview for at most 30 seconds, loopback-only
  private URL, bounded HTTP requests, Host/Origin checks, no recording or inference.
  Expiry/Stop clears the slot and closes capture. Static test page is available at
  `/live/obs-test`; ordinary `/live` remains idle until later browser/API integration.

The backend is installed **FFmpeg n9.0.1 V4L2**, using argument arrays, input queue
size one, passthrough frame timing and flushed PPM output. PPM preserves frame
boundaries/dimensions. Real producer timestamps/sequences remain null; locally
assigned receipt sequence/time is never presented as OBS render time.

Linux's documented extended-color capability/magic rules are enforced. Legacy
metadata uses documented colorspace defaults. The actual selected YUYV source
declares sRGB with default BT.601 encoding and limited range; those defaults are
explicitly accepted and converted. References: [V4L2 pixel formats](https://cdn.kernel.org/doc/html/latest/userspace-api/media/v4l/pixfmt-v4l2.html),
[V4L2 color defaults](https://www.kernel.org/doc/html/v6.1/userspace-api/media/v4l/colorspaces-defs.html),
[FFmpeg options](https://www.ffmpeg.org/ffmpeg-all.html), and
[OBS v5 protocol](https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md).

## Consent and actual host checks

Initial work used sysfs/stat metadata and synthetic sources only. The operator
subsequently explicitly selected `/dev/video0`, label **OBS Virtual Camera**, fixed
scene **FLYJAM_INPUT**, their selected monitor source, and authorized local preview
and bounded OBS01 validation. Setup evidence was read from
`/home/kernel_sanders/.local/share/flyjam/evidence/20260915-obs-setup/setup.json`.
No other capture device was opened.

Confirmed actual configuration: v4l2loopback **0.15.4-2**, kernel
`7.2.4-arch1-2`; driver string `v4l2 loopback`, card `OBS Virtual Camera`, device
number 20736, inode 1299, **1920×1080, YUYV, 60/1 fps**, stride 3840, image size
4,147,200 bytes. Active capabilities `0x05200001`; `keep_format=0`,
`sustain_framerate=0`, `timeout=0`. Extended color metadata is supported.
OBS WebSocket is enabled on 4455 with authentication disabled. It was not used
for verified monitoring and its settings were not changed.

1. First approved preview: **262 frames accepted**, 242 replaced during a slow
   consumer, 5.10 seconds including cleanup. Matching source/encoded identity
   assertions passed. Only one 16×16 processed input plus metadata was saved.
2. Actual operator stop: driver sysfs state changed `capture` → `output`, and
   capabilities became output-only `0x05200002`. Capture entered `source_lost`
   **0.06068 seconds after the sampled driver transition**; FFmpeg was reaped.
   The transition was sampled every 20 ms, so this is not a precise measurement
   from the human click. **1,305 frames** were accepted during the bounded probe.
   No image was saved for that probe.
3. The operator restarted Virtual Camera explicitly. A fresh revalidated
   five-second CLI/browser preview accepted **296 frames**, showed active driver
   status, matched displayed canvas bytes to the displayed observation hash,
   had zero page errors, expired, and closed capture. No automatic capture resumed.
4. The operator displayed the original test page and confirmed markers in the
   existing scene preview. Two early probes failed the marker detector; a separate
   bounded diagnostic initially found qualifying areas of 8/0/0 pixels. One
   **320×180 source thumbnail**, stored privately, then showed the actual test page
   correctly oriented. Its green marker was RGB `[41,255,20]`, just outside the
   diagnostic's overly strict maximum-40 secondary-channel cutoff. The diagnostic
   was corrected to recognize dominant primary colors, with one second of initial
   draining; the sensory encoder and OBS configuration were not changed.
5. Final actual OBS pattern probe: **five samples passed** RGB orientation and
   visible-counter checks; counters advanced **28,988 → 29,508** while capture
   sequence advanced **46 → 433**. Deliberately slow OCR/consumer intervals were
   **1.62–1.78 seconds**; receipt ages were **16.9–32.8 ms**. The reader accepted
   **527 frames** and replaced **521**. Counter OCR was diagnostic-only, in memory,
   never supplied to the encoder/controller; other recognized text was discarded.
   This supports continuous draining and recent frame consumption. Absolute
   producer-to-consumer latency remains unknown because producer timestamps are
   unavailable; no stronger timing claim is made.

Driver stop reasoning was checked against the installed
`/usr/src/v4l2loopback-0.15.4/v4l2loopback.c` and
[upstream 0.15.4 source](https://github.com/v4l2loopback/v4l2loopback/blob/v0.15.4/v4l2loopback.c).
`keep_format` can preserve capture capability after producer stop; verified driver
mode therefore requires it off and terminates if that configuration changes.
Capture capability proves a producer stream exists, not that the captured app is
animating. Lost/expired monitoring cannot renew verified status through pixels.

## Validation and evidence

Evidence root: ignored [`artifacts/milestones/OBS01/`](../../../artifacts/milestones/OBS01/).
Counts overlap and must not be summed as unique tests. Passing suites below have
zero failures, errors and skips. No real-model tests or hosted CI were run.

| Actual command / operation | Result | Evidence |
|---|---|---|
| `make verify-live LIVE_EVIDENCE=artifacts/milestones/OBS01/final` | Exit 0: **281 Python live**, **93 UI/contracts**, **124 Python lab**, **15 lab UI**, **2 idle-browser** passes; schema drift, Ruff, TypeScript/build passed | `final.command.json`, `final.log`, `final/` |
| Actual FFmpeg fixture with visible pixel indices and slow consumer | PASS; increasing recent indices, replacement counts, no growing pipe backlog | `capture-color.log`, final Python suite/log |
| Actual FFmpeg RGB/BGR/YUYV/NV12 fixture conversion | PASS; channels/orientation and full/limited BT.601 range checked | maintained capture tests / final suite |
| Fixture CLI HTTP and producer faults | PASS; source/hash agreement, privacy controls, absolute request deadline, expiry, stop race, uncooperative child, driver/OBS heartbeat expiry | maintained live tests / final suite |
| Actual Chromium fixture preview, desktop/mobile | PASS; matching previews/IDs, expiry, no page errors or overflow; screenshots visually inspected | `preview/browser-report.json`, `preview/*-final.png` |
| Metadata-only devices/doctor | Both exit 0; no capture from those commands | `devices.command.json`, `doctor.command.json`, `host/` |
| Selected `inspect-source` and explicit `v4l2-ctl --device /dev/video0` metadata | PASS after sRGB default handling repair; actual stopped capability transition recorded | `selected-device.json`, `selected-device.txt`, `stopped-device.txt` |
| `python -m artifacts.milestones.OBS01.real_preview` | Exit 0, actual real preview | `real-preview.log`, `real-source/preview.json` |
| `python -m artifacts.milestones.OBS01.stop_probe` | Exit 0, actual operator stop | `stop-probe.log`, `real-source/producer-stop.json` |
| `python -m artifacts.milestones.OBS01.restart_preview` | Exit 0, actual browser/expiry after restart | `restart-preview.log`, `real-source/restart-preview.json` |
| `python -m artifacts.milestones.OBS01.pattern_probe` | Exit 2, required markers absent | `pattern-probe.log`, `real-source/pattern.json` |
| `python -m artifacts.milestones.OBS01.pattern_probe_confirmed` | Exit 2, detector cutoff still rejected markers | `pattern-confirmed.log`, `real-source/pattern-confirmed.json` |
| `python -m artifacts.milestones.OBS01.pattern_probe_final` | Exit 0, actual RGB markers/orientation and visible counter progression | `pattern-final.log`, `real-source/pattern-final.json` |

Real commands above use `.venv/bin/python`. Scripts, exact arguments, reports and
source identities remain local evidence. No full-resolution desktop frame or video
was written; the real-source directory contains measurements, exact 16×16
processed inputs and the single necessary 320×180 diagnostic thumbnail. All stay
local and ignored. Fixture screenshots contain synthetic content only.

Earlier integrated validation passed 259 live tests; the later targeted suite
passed 262. Review then added driver-mode checks and real-device color support;
the final integrated suite above supersedes their counts. Earlier failures and
development reports remain preserved. Review repaired extended-color metadata
handling, Start/Stop races, bounded subprocess reaping and slow-header preview
expiry. Two fixture browser harness attempts failed due to harness assumptions
(CSP string evaluation and terminal wording), then passed after harness repair.
One producer auth test initially had an incorrect fixture digest, corrected using
an independent SHA256 calculation. Existing Starlette/AnyIO deprecation and
Playwright color-environment warnings remain visible.

## Handoff

`source-identity.json` records the baseline, final working-tree hashes and changed
files. All 47 explicitly protected model/kit/notice/lock files match the baseline;
the P00 ledger hash matches OBS00 and still contains 144 attempts. `cleanup.json`
confirms no owned FFmpeg capture remains. Changes are in the working tree; no
commit, push, PR or publication was performed.

Safe synthetic preview:
`.venv/bin/python -m flytrap.live preview --source fixture-pattern --seconds 15`.

Approved real preview:
`.venv/bin/python -m flytrap.live preview --source v4l2-video0 --seconds 15 --verified`.
It prints the private local URL, uses reliable driver status on this setup, and
expires. No shell script is needed. Use `--port` if its default 8768 is occupied.

OBS02 is the next independent milestone on the next invocation. No model worker,
flight decoder, session recording/replay implementation or whole-pipeline model
gate was executed in OBS01. Final real-model/OBS/causal gates belong to OBS06.
There are **no remaining OBS01 blockers**. The authenticated OBS-monitor path is
fixture-tested; actual authentication remains disabled in the existing OBS config
and was unnecessary for this verified driver. Drivers lacking reliable status
will need authenticated monitoring. Human product approval remains separate.
All owned capture/preview processes stopped; the user-restarted Virtual Camera
was left running. No scene/settings, OBS recording/streaming or privileged host
changes were made by the agent. Stop after OBS01.
