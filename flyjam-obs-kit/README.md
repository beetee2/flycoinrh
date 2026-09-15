# Flyjam — OBS-to-flight implementation kit

Reviewed upstream checkout: `beetee2/flycoinrh`, commit
`a1af684f5dbcf88f75cc23da5b0df6621a7efd5a`.
Prepared September 15, 2026. Verify the actual local checkout before editing.

This kit contains implementation instructions, not an implemented application
or a report of tests executed by the kit's author.

## Target

A selected local OBS Virtual Camera feed drives the existing connectome adapter.
The resulting neural responses drive a recognizable fly in a third-person browser
scene. The operator can preview, start, stop, inspect, and optionally record/replay
a bounded session. No fly-eye camera is required.

## Install the instructions

Extract this kit so `flyjam-obs-kit/` sits at the root of the existing fork,
alongside `flytrap/`, `web/`, and `AGENTS.md`. Do not replace `flytrap-kit/`.

## First message to the coding agent

```text
Implement the local Flyjam OBS-to-flight assignment in this checkout.

This authorizes the new OBS00–OBS06 workstream described in flyjam-obs-kit/.
It supersedes the P00-only stop for this new workstream. It does not approve
historical navigation, public release, token work, or unrelated later milestones.

Read applicable AGENTS.md instructions, flyjam-obs-kit/SPEC.md,
flyjam-obs-kit/TEST_MATRIX.md, and docs/implementation/STATUS.md.
Then read and execute only:
flyjam-obs-kit/prompts/00-scope-and-contracts.md

Implement and test the requested deliverables. Preserve my existing changes.
Record actual commands, results, evidence, and the next handoff; then stop.
No external writes, public tunnels, paid services, or privileged system changes
are authorized. Ask before capturing a device/source I have not selected.
```

## Exact execution order

Each line is a separate message to the coding agent, after the preceding
milestone's implementation requirements are met:

```text
Read flyjam-obs-kit/SPEC.md and execute only flyjam-obs-kit/prompts/01-capture.md.
```
```text
Read flyjam-obs-kit/SPEC.md and execute only flyjam-obs-kit/prompts/02-neural-session.md.
```
```text
Read flyjam-obs-kit/SPEC.md and execute only flyjam-obs-kit/prompts/03-flight.md.
```
```text
Read flyjam-obs-kit/SPEC.md and execute only flyjam-obs-kit/prompts/04-api-and-replay.md.
```
```text
Read flyjam-obs-kit/SPEC.md and execute only flyjam-obs-kit/prompts/05-browser.md.
```
```text
Read flyjam-obs-kit/SPEC.md and execute only flyjam-obs-kit/prompts/06-validation-and-handoff.md.
```

Alternatively, after OBS00, repeatedly send:

```text
Read and execute flyjam-obs-kit/RESUME.md.
```

This resume file is specific to OBS00–OBS06. Do not use the older navigation
resume. An invocation completes one milestone and stops.

## Human setup and reviews

1. The agent inspects the environment and lists capture-device metadata.
2. In OBS, create `FLYJAM_INPUT`, choose the intended content, and pin Virtual
   Camera to that scene. Start Virtual Camera; broadcasting is unnecessary.
3. Identify the intended virtual device and approve its safe preview. Do not
   use personal messages, credentials, or unapproved third-party material as
   validation content. Keep the Flyjam output out of the input scene.
4. Approve any necessary host package/kernel/permission setup individually.
   If reliable OBS-stop detection needs a read-only OBS WebSocket monitor,
   enable its authenticated local connection; do not paste its password into chat.
5. After OBS05, inspect the actual fly, movement, framing, and responsiveness.
6. After OBS06, approve the local experience or give concrete changes. This is
   separate from deployment or product/contest approval.

While hardware setup is pending, the agent should finish independent code and
fixture validation. Hardware-pending does not authorize a fake real-source pass,
but it also does not require stopping all unrelated implementation work.

## Completion states

`implementation_status`, `real_model_status`, `real_obs_status`,
`causal_validation_status`, and `human_review` are separate fields.
A successful synthetic demonstration is not a successful OBS demonstration.
The old navigation release gate remains unchanged and blocked.
