# Prompt 05 — Real-model feasibility and task calibration gate

Read AGENTS.md, flytrap-kit/PLAN.md, flytrap-kit/BOUNDARIES.md, and docs/implementation/STATUS.md before editing. Follow the milestone evidence protocol. Implement only this milestone, run the appropriate tests, inspect the outputs, update status and handoff notes, then stop. Never claim unexecuted tests passed or replace a missing real model with an undisclosed fixture.

Run the actual model and arena together before building the product shell. Use the full graph and actual fly adapter, not the synthetic controller. Measure cold load time, peak memory, step-latency distribution, actual trajectory/outcomes, finite motor activity, and observation hashes across fixed seeds.

Use development-only trials to examine bright/dark/patterned inputs, blank-input controls, left/right layout swaps, freezing/stuck behavior, and the effect of motor scaling. Measure whether distinct pixels influence outputs; do not equate movement or changing weights with learning. Do not require the fly to succeed at an arbitrary task to consider the pipeline functional.

Write a small reproducible JSON/Markdown report with hardware/software/data hashes, complete development trial IDs, failures, and the selected preset/action mapping. Freeze that configuration before held-out evaluation. Set proposed admission/latency/episode budgets from measured cost, not guesses.

Choose an honest interaction mode: live progress when usable, otherwise queued computation and explicitly labeled replay. A minimal preset can replace an overambitious arena based on development evidence; never alter a trajectory secretly. If real data cannot run, mark the real-model gate BLOCKED. Do not fabricate a successful example or proceed as if fixture evidence validated the model. End with a concrete go/no-go for the playable core.
