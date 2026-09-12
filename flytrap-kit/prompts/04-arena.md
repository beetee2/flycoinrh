# Prompt 04 — Deterministic arena, rendering, and outcome rules

Read AGENTS.md, flytrap-kit/PLAN.md, flytrap-kit/BOUNDARIES.md, and docs/implementation/STATUS.md before editing. Follow the milestone evidence protocol. Implement only this milestone, run the appropriate tests, inspect the outputs, update status and handoff notes, then stop. Never claim unexecuted tests passed or replace a missing real model with an undisclosed fixture.

Implement the constrained two-choice arena as a pure fixed-step state machine. Use two reachable patterned destination pads, a lower start, and zero to three allowed distractions. Define legal presets, margins, overlap/reachability checks, trial tick limits, terminal tie-breaking, and explicit success/wrong-pad/timeout outcomes. Keep cue-to-reward mapping consistent within the task/cohort.

Build one authoritative grayscale renderer. The same raster feeds the retina and is displayed by the browser later. Human labels, paths, avatar decoration, scores, and debug information belong in a separate overlay and never enter the observation. Freeze crop, pixel normalization, boundary sampling, and texture versions.

Apply bounded model actions without attraction to goals, hidden steering, rescue teleports, or scripted success. Use swept collision/goal intersection so large steps cannot skip obstacles or terminal pads. Keep wall time distinct from environment ticks and neural milliseconds.

Use pytest, property-based tests, and golden pixels for identical-seed replay, clipping, legal generation, terminal behavior, texture/crop consistency, and nonfinite input rejection. Add an information-flow test: identical observation/checkpoint/seed with changed hidden scoring metadata produces identical controller output. Test physics with known scripted controllers only as labeled test fixtures. Produce inspectable sample frames and trajectories, not claims of model competence.
