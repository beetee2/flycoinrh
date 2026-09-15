# OBS05 — usable OBS-to-flight screen

Read `flyjam-obs-kit/SPEC.md`, `flyjam-obs-kit/TEST_MATRIX.md`, applicable
`AGENTS.md`, actual git status, `docs/implementation/OBS-STATUS.md` if present,
and the latest relevant milestone report. Read the relevant implementation before
editing. Perform the actual work, run appropriate tests, and update the handoff.
Preserve user changes and existing evidence. Execute only this milestone.

Complete the operator experience around the actual live services.

1. Deliver `/live` with the fly stage as the primary visual, a source selector,
   explicit Preview, Start/Stop, session bounds/seed, record-replay consent and
   current status. A small approved source preview and exact last-inferred input
   belong behind a clear inspection toggle; neural tables are not the main page.
   Keep `/lab` working as a separate diagnostic experience.

2. Use strict runtime validation of every response/event. Display capture rate,
   neural update rate and rendering rate separately, with relevant ages and
   source/model mode. Properly label waiting, disconnected, stale, failed,
   replay and synthetic modes. Never smooth a failure into fake Live behavior.
   Make late/foreign-session packets harmless and show accepted input IDs.

3. Connect the actual server-authoritative flight state to the renderer. Smooth
   between legitimate snapshots without unbounded prediction. Browsers/tabs at
   different frame rates must not produce different authoritative trajectories.
   On transport loss or expired state, stop visual translational advancement
   within the documented limit. One renderer loop per mounted stage, cleanup on
   unmount, visible-tab/lease policy, clear browser-back/reload behavior.

4. Complete replay list/load/pause/seek, labeled recording playback and evidence
   download. No inference on replay or UI edit. Include clear artifact/privacy
   handling. Rendered controls/poses and downloaded trace refer to the same run.

5. Refine appearance with actual screenshots: identifiable fly silhouette,
   attractive restrained scene, useful scale/depth, visible turns and motion,
   readable status, keyboard-operable controls and responsive layout. Previewing
   or recording must not accidentally capture the output window. No need for a
   fly-eye camera, audio, token UI, gallery accounts or public publishing.

Validation: meaningful Vitest/Testing Library tests, keyboard/accessibility checks,
actual fixture-service Playwright journeys, small/desktop viewport, preview and
Start/Stop/error/replay paths, stale state and cleanup. Include a real-model
journey using the safe source under the workstream budget, and actual OBS when
approved/available. Test displayed neural values, accepted observation bytes and
server flight state—not only that a canvas exists. Open and inspect the screenshots.

Handoff: exact verified startup command/URL and a short hands-on checklist. Record
implementation status separately from real-OBS and human taste. The human should
now try their approved OBS scene and judge motion/framing/responsiveness. Stop;
OBS06 performs the final integration and maintenance checks when instructed.
