# Prompt 03 — Real fly adapter and information isolation

Read AGENTS.md, flytrap-kit/PLAN.md, flytrap-kit/BOUNDARIES.md, and docs/implementation/STATUS.md before editing. Follow the milestone evidence protocol. Implement only this milestone, run the appropriate tests, inspect the outputs, update status and handoff notes, then stop. Never claim unexecuted tests passed or replace a missing real model with an undisclosed fixture.

Implement the real FlyController adapter behind the Observation/ControllerOutput contracts. Inject graph, annotations, model parameters, calibration, and checkpoint paths explicitly. It must run independently of the current working directory and must not import roaming, wallet, or token-launch services.

Provide reset(run_seed, checkpoint) and step(observation). Only bounded grayscale observation pixels may cross the task-input boundary. No goal coordinates, challenge object, target label, reward, DOM, or distance-to-goal is available during evaluation. Define the task-independent per-step seed stream and bounded motor mapping. Label the preserved upstream behavior windowed_reset; do not silently add continuous membrane state.

Do not implicitly load prior mushroom-body state or upstream trained gains. Use an explicit untrained baseline. Validate required neural populations and finite output; errors must not trigger random or scripted fallback. Optimize repeated annotation loading only while preserving behavior.

Test path independence, reset isolation, repeatability with fixture graphs, malformed inputs, numeric bounds, no checkpoint contamination, and the serialized observation envelope. Check centered-crop sampling parity with FlyEye. Add architectural/import tests against privileged environment dependencies. Run a real-data adapter smoke when available and distinguish it from fixture results. Record actual performance without a real-time claim.
