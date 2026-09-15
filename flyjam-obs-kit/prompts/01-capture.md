# OBS01 — OBS frame source, preview and exact Observation

Read `flyjam-obs-kit/SPEC.md`, `flyjam-obs-kit/TEST_MATRIX.md`, applicable
`AGENTS.md`, actual git status, `docs/implementation/OBS-STATUS.md` if present,
and the latest relevant milestone report. Read the relevant implementation before
editing. Perform the actual work, run appropriate tests, and update the handoff.
Preserve user changes and existing evidence. Execute only this milestone.

Implement the real source adapter plus a safe deterministic test source.

1. Implement source discovery/selection and bounded opening for an explicitly
   approved V4L2 OBS virtual device. Validate resolved device, driver/capabilities,
   pixel format, dimensions, rate and permissions. Do not probe by capturing every
   camera, default to /dev/video0, or substitute webcams/files on error.

2. Build continuous capture with a capacity-one latest-frame slot. Separate it
   from inference, include source epochs/sequences/receipt timestamps, and handle
   blocked reads, partial frames, format changes, EOF, stop, and cleanup. If using
   FFmpeg, use argument arrays; drain stdout/stderr and keep diagnostics bounded.
   Verify actual upstream buffering with a source carrying visible frame indices.
   No image equality-based automatic stop: a static scene is legitimate.

3. Add producer-state monitoring required by SPEC. Test actual virtual-camera
   stop behavior. If the driver repeats frames and lacks trustworthy producer
   status, implement the read-only authenticated local OBS monitor. Unsupported
   status cannot silently become a verified Live label. Do not modify OBS itself.

4. Implement obs-rgb-letterbox16-v1 as a pure encoder. Pin its precise color,
   aspect-ratio, resize, rounding and padding rules. Keep normalized Observation
   and exact uint8 bytes/hash together. No brightness adaptation/content targeting.
   Provide a latest-source preview and exact encoded preview with matching IDs.
   Preview starts only on an explicit operator action and expires without neural
   work. It must not persist raw desktop images.

5. Add a source-neutral deterministic test/replay implementation for fixture CI.
   It must be explicitly selected and labeled. Generate an original harmless
   test page/clip with moving shapes and frame counters for the operator's OBS
   scene; do not use their private desktop for automated validation.

Validation: unit/property/golden pixel tests, channel order/orientation/letterbox,
large/malformed frames, stale epochs, same pixels with new timing, slow-consumer
recent-frame assertions, reader-stop/hang failures, producer-status simulation,
and real-backend preview with the selected approved source when available.
No neural model calls are needed in this milestone.

Handoff: report the actual device/config and whether real capture and OBS-stop
signaling were verified. Ask only for missing specific host setup/source consent.
When hardware is unavailable, finish safe implementation/fixture checks and mark
real_obs_status PENDING or BLOCKED. OBS02–OBS05 may proceed with the declared test
source; final verified completion still requires actual OBS. Stop.
