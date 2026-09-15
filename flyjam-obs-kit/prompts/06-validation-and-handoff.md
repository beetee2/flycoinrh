# OBS06 — real OBS acceptance, causality, CI and final handoff

Read `flyjam-obs-kit/SPEC.md`, `flyjam-obs-kit/TEST_MATRIX.md`, applicable
`AGENTS.md`, actual git status, `docs/implementation/OBS-STATUS.md` if present,
and the latest relevant milestone report. Read the relevant implementation before
editing. Perform the actual work, run appropriate tests, and update the handoff.
Preserve user changes and existing evidence. Execute only this milestone.

Finish the assignment rather than proposing another pivot.

1. Review OBS00–OBS05 against SPEC/TEST_MATRIX and the actual code. Resolve concrete
   defects. Ensure every required make target performs real work and returns
   meaningful failures. Keep historical navigation release checks unchanged.
   Evidence must identify the tested checkout, configuration and environment.

2. Make ordinary CI include lab + live schema drift, component tests and separate
   fixture-browser journeys, as well as existing required checks. Dedicated real
   model/OBS targets must fail nonzero for missing requirements. Do not ask hosted
   PR CI to install a kernel module, open hardware, or download private recordings.
   Preserve the managed-runtime CI correction and use isolated evidence paths.

3. Execute the real-model gate, then the real-OBS gate using the operator-selected
   device and approved safe content. A real fixture-source test is not an OBS
   pass. Check Start, source changes, responsive health, explicit Stop, actual
   virtual-camera stop, source restart, no backlog, late-worker results, control
   tab closure/lease expiry, opt-in record and zero-call replay. Confirm no orphan
   subprocesses, leaked locks, raw desktop files or exposed secrets. Do not infer
   source health from identical/different pixels alone.

4. Run the bounded input-influence comparison from TEST_MATRIX on recorded safe
   observations: changing, frozen and actually disconnected drive, matched seeds,
   one exact repeat. Freeze the schedule first and use the remaining workstream
   allowance. The disconnected control must be an explicit diagnostic hook;
   black input is not neural silence. Do not mutate baseline files or pretend
   diagnostic ablations are ordinary live-mode outputs. Compare rates, decoded
   controls and flight state with fixed initial pose and playback timing.

5. Measure capture/receipt ages, encoding, model load/step latency, stale output
   rejection, capture overwrites, API responsiveness, rendering and session RSS
   separately. Include a small slow-consumer/failure soak within explicit bounds.
   Report measured values without equating wall time, neural simulated time or
   renderer FPS. Do not benchmark by changing the model fidelity.

6. Produce `docs/implementation/OBS-LIVE-HANDOFF.md`, current OBS-STATUS, final
   report and a private review bundle from safe approved content. Include actual
   commands/results, startup/setup instructions, exact source configuration,
   source/model/encoder/decoder identity, screenshots, a short real flight capture
   when feasible, optional replay, remaining limitations and cleanup/recovery.
   Desktop content or footage stays local; sanitize anything proposed for sharing.

7. Stop with a clear final result:
   - implementation_status
   - real_model_status
   - real_obs_status
   - causal_validation_status
   - human_review

If hardware or permission is missing, finish all independent code and tests and
return BLOCKED only for the affected gate, with the exact minimum operator action
and rerun command. Do not report complete verified OBS integration. If the neural
mapping yields weak visual variation, report the measurements and request a scoped
mapping change; do not invent an impressive result or abandon the integrated app.

No public deployment, token work, remote push, PR, privileged system changes or
social publication. Final human approval concerns this local experience only.
