# FLYTRAP implementation kit

This kit specifies the work; it does not contain an implemented FLYTRAP app or executed test results.

## Start

Unpack the archive into the root of a local flycoinrh fork, retaining the `flytrap-kit/` folder. Do not overwrite an existing project folder containing your own work. Open that checkout in your coding-agent workspace with GPT-6 Astra and working shell/filesystem/browser-test tools.

Paste `prompts/00-audit.md`. After that milestone reports its actual validation status, paste `01-foundation.md`, then continue numerically through `18-submission.md`. All prompts are also combined in PROMPTS.md. The complete plan is PLAN.md and boundary validation requirements are BOUNDARIES.md.

Do not advance past a failed technical prerequisite. An inconclusive learning result is not a failed core product: continue with learning claims and comparisons disabled. Missing actual-model execution is a blocker for a real-model release. Deployment and posting require explicit authorization and working access.

## New-session resume prompt

```text
Resume FLYTRAP in this checkout. Read AGENTS.md, flytrap-kit/PLAN.md,
flytrap-kit/BOUNDARIES.md, docs/implementation/STATUS.md, and the latest
milestone evidence. Check actual git status and prerequisites. Do not trust
old chat summaries in place of artifacts. Execute only the next numbered
prompt whose prerequisites are met, using its file in flytrap-kit/prompts/.
Report real validation results and stop at that milestone boundary.
```

## Contents

- PLAN.md — product, architecture, contracts, data flow, storage, safety, research, and release design.
- BOUNDARIES.md — test types, invariants, required tools, and evidence for every layer.
- PROMPTS.md — the complete copy-ready prompt sequence.
- prompts/ — each numbered prompt as a separate file.
- SOURCES.md — inspected upstream code and primary documentation.
- manifest.json — prompt order and kit checksums.

Use these as implement-and-validate tasks, not requests for further planning only. No prompt authorizes token transactions, paid hosting, remote pushes, PR creation, or social posting by itself.
