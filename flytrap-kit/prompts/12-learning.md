# Prompt 12 — Optional, explicit learning implementation

Read AGENTS.md, flytrap-kit/PLAN.md, flytrap-kit/BOUNDARIES.md, and docs/implementation/STATUS.md before editing. Follow the milestone evidence protocol. Implement only this milestone, run the appropriate tests, inspect the outputs, update status and handoff notes, then stop. Never claim unexecuted tests passed or replace a missing real model with an undisclosed fixture.

Implement learning behind a default-off feature flag and an offline/operator-only training command. Reuse the preserved anatomical metadata, not signed fast weights, for documented PAM/PPL1→MBON classification. Treat ties, zero input, and ambiguous assignments explicitly; the classification is a model heuristic, not proof of biological validity. Inspect current calibration.py but do not assume odor calibration validates visual learning.

Restrict updates to allowed KC→MBON synapses with tested eligibility, bounded reward events/gains, declared recovery, and explicit timing. Load a pristine baseline and apply a checkpoint exactly once. Provide immutable checkpoints whose manifests bind graph/body/synapse mappings, gains, learning parameters, source, training data, and calibration. Reject corruption or mismatch loudly; remove implicit autoload and swallowed-error behavior from this path.

Training receives outcomes only after observations/actions. Evaluation cannot update, forget, or save gains. Validate/deduplicate community-derived layouts into candidate training data; never allow public requests to mutate the active model or supply arbitrary checkpoint files.

Test selective versus protected weight changes, event signs/bounds, inactive traces, ties, repeated load, no double application, crash-safe saves, graph mismatch, and isolation across runs. Run a small real-data learning smoke measuring what changes and KC activation; do not call it task improvement. Mechanical PASS with learning still unproven is an acceptable milestone result.
