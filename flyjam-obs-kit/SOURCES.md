# Source notes

Repository inspection is pinned to `a1af684f5dbcf88f75cc23da5b0df6621a7efd5a`.
The kit does not independently certify the user's locally reported real-model tests.

## Existing implementation

- https://github.com/beetee2/flycoinrh/blob/a1af684f5dbcf88f75cc23da5b0df6621a7efd5a/AGENTS.md
- https://github.com/beetee2/flycoinrh/blob/a1af684f5dbcf88f75cc23da5b0df6621a7efd5a/docs/implementation/STATUS.md
- https://github.com/beetee2/flycoinrh/blob/a1af684f5dbcf88f75cc23da5b0df6621a7efd5a/flytrap/controllers/fly.py
- https://github.com/beetee2/flycoinrh/blob/a1af684f5dbcf88f75cc23da5b0df6621a7efd5a/flytrap/lab/api.py
- https://github.com/beetee2/flycoinrh/blob/a1af684f5dbcf88f75cc23da5b0df6621a7efd5a/flytrap/lab/sensory.py
- https://github.com/beetee2/flycoinrh/blob/a1af684f5dbcf88f75cc23da5b0df6621a7efd5a/flytrap/lab/runner.py
- https://github.com/beetee2/flycoinrh/blob/a1af684f5dbcf88f75cc23da5b0df6621a7efd5a/Makefile
- https://github.com/beetee2/flycoinrh/blob/a1af684f5dbcf88f75cc23da5b0df6621a7efd5a/web/package.json

Important integration facts from those files: P00 remains an explicitly local
prototype; its per-request A/A-repeat/B runner is not a live frame loop;
FlyController binds baseline identity to source/config and restricts observations
to pixels; sensory.py currently rereads annotations while constructing the oracle;
Makefile exposes lab checks separately from ordinary verify.

## Primary technical references

- OBS Virtual Camera guide: https://obsproject.com/kb/virtual-camera-guide
  (A particular scene/source can be selected independently of normal program output.)
- Linux virtual camera setup: https://obsproject.com/kb/virtual-camera-troubleshooting
  (Linux uses v4l2loopback; host setup is distribution/kernel dependent.)
- V4L2 API: https://docs.kernel.org/userspace-api/media/v4l/v4l2.html
- v4l2loopback README: https://github.com/v4l2loopback/v4l2loopback
  (sustain_framerate can duplicate frames; timeout images are configurable;
  a read or identical image is not a complete producer-liveness signal.)
- FFmpeg input devices: https://ffmpeg.org/ffmpeg-devices.html#video4linux2_002c-v4l2
- OBS WebSocket: https://github.com/obsproject/obs-websocket
  (Use only authenticated local read-only status operations if needed.)
- Playwright managed test servers: https://playwright.dev/docs/test-webserver
- Codex repository instructions: https://developers.openai.com/codex/guides/agents-md

Validate the actual installed backend and protocol against current primary docs.
All new time/call/storage limits and UI/flight choices in this kit are proposed
engineering defaults, not claims from OBS documentation or performance measurements.
