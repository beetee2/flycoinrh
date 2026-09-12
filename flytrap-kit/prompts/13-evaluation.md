# Prompt 13 — Controlled evaluation and evidence-based claim gate

Read AGENTS.md, flytrap-kit/PLAN.md, flytrap-kit/BOUNDARIES.md, and docs/implementation/STATUS.md before editing. Follow the milestone evidence protocol. Implement only this milestone, run the appropriate tests, inspect the outputs, update status and handoff notes, then stop. Never claim unexecuted tests passed or replace a missing real model with an undisclosed fixture.

Implement the evaluation protocol in PLAN.md. Before held-out evaluation, commit/hash the task families, cue mappings, training budget, seed blocks, primary/secondary metrics, exclusions, candidate selection, stopping rule, and proposed meaningful-effect threshold. Separate train/validation/test by layout family. Tune only on development data and keep the held-out test untouched until the configuration is frozen.

Compare trained/frozen against identical untrained/learning-disabled and shuffled-reward controls. Add development-calibrated matched-speed random and blank-observation controls. Use paired challenge/seed blocks, fixed action mapping, and immutable evaluation checkpoints; verify weight/config hashes before and after. Account for every scheduled episode, timeout, failure, and exclusion.

Implement analysis with hand-calculated fixtures and null-effect synthetic checks. Estimate paired uncertainty at the independent layout/cohort level, not from correlated timesteps. Report success fraction, carefully defined steps-to-outcome, wrong-pad/timeout rates, and wall cost. A small pilot is explicitly exploratory; do not manufacture sample size or statistical confidence.

Run the declared experiment within measured resource budgets. Produce machine-readable and readable reports, full trace references, and SUPPORTED/UNSUPPORTED/INCONCLUSIVE/NOT_RUN claim status. Only a qualifying report bound to the exact checkpoint/config enables trained-improvement claims. Negative or inconclusive evidence must keep the feature disabled while allowing the validated core to ship. Do not reroll seeds until a favorable result appears.
