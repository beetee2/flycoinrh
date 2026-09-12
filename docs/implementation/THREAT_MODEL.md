# FLYTRAP threat model — audit 00

This records threats and required controls. The table preserves audit 00 findings;
the foundation update below records controls now exercised. Scope is the wallet-free
local challenge architecture in
[PLAN](../../flytrap-kit/PLAN.md) and its [boundary tests](../../flytrap-kit/BOUNDARIES.md).

Assets: honest controller behavior and scientific claims; immutable data/checkpoint
provenance; durable challenges, attempts, and replays; host CPU/RAM/disk capacity;
visitor session integrity; operator credentials and unrelated local files.

| Boundary / threat | Required control and evidence | Current audit evidence |
|---|---|---|
| Upstream startup → external side effects | Dedicated FLYTRAP entrypoint, no upstream launch/roam/voice imports or credential mounts; verify production process/config. | `roam.py:177-253,781-807` can open a public tunnel and publish its address; blob helpers can write externally. `run_all.py` can enable the narrator. Docker defaults enable browsing. Inspected only. |
| Public request → compute exhaustion | Strict schemas/body limits, same-origin sessions, trusted proxy config, atomic per-session/source/global quotas, bounded queue/streams/disk. | No FLYTRAP API exists. |
| Arena → privileged controller input | Pixels-only serialized envelope, controlled imports, no planner/hidden steering; same pixels/seed/checkpoint must give the same action after hidden-score changes. | Current pilot consumes pixels and cursor location; adapter still required. |
| Data/checkpoints → silent model change | Approved IDs, immutable checksummed data, explicit loads, shape/range/mapping validation; preserve discarded anatomical edges. | MushroomBody auto-loads and swallows errors; compartment lookup direction is wrong. |
| Queue → duplicate or hung compute | Exclusive host slot, transactional claim, leases/fencing, independent heartbeat, resource deadline, bounded retry history. | No durable queue or FLYTRAP worker exists. |
| Worker → missing/forged completed replay | Crash-tested fsync/rename/DB publication, immutable bundles, safe paths, digests, orphan reconciliation. | No FLYTRAP artifacts exist; evidence files from this audit are not replays. |
| Replay/download → path traversal or oversized payload | Server-approved IDs, root confinement, bounded compressed/decompressed sizes, chunk/order/schema/digest validation. | Future boundary tests required. |
| HTTP/SSE → identity bypass, stale or lost state | Origin checks, secure cookies, explicit proxy trust, event sequences/attempt IDs, reconnect/dedupe and terminal recovery against real sockets. | Upstream websockets/CORS do not implement these contracts. |
| UI/marketing → fabricated model or learning claim | Persistent fixture labels, real telemetry only, disclosed playback speed, provenance links and report-dependent claim gate. | Upstream README/calibration numbers are assertions, not audit measurements. |
| Container/storage → data loss or secret access | Unprivileged processes, read-only model data, local persistent volumes, tested restore, no host-home/wallet/SSH/Docker-socket mounts. | Dockerfile uses a floating Python tag, no USER, and copies all root Python modules. Not built or launched. |

Trust the operator to install reviewed source and approved model assets. The
information-flow test is interface evidence, not a sandbox against malicious code
with unrestricted host access. Anonymous limits deter abuse without establishing
one person per session. Checksums establish consistency within declared versions;
they do not establish biological validity or authorship of an entire dataset.

Audit execution used the repository's offline unit tests. Their fake publication
messages are captured in logs; they are not actual social posts. Wallet/chain
entrypoints, public services, paid resources, deployment commands, and live
experiments were not run. No security or load gate is claimed as passing.


## Foundation 01 update

Executed tests now verify strict request/response structure, bounded finite numbers,
path-like ID rejection, explicit fixture identity, production fixture rejection,
absence of upstream service imports, SQLite minimum rejection, real file connection
lifecycle, and a separate worker process with bounded observation messages. The UI
rejects malformed API responses and visibly labels synthetic operation. Doctor's
model-file presence checks are explicitly labeled upstream checkout probes; storage
roots are operator configuration, not caller-provided paths.

These checks do not establish durable queue recovery, immutable replay publication,
public admission/security controls, container hardening, model behavior, or learning
benefit. The real/release commands return nonzero BLOCKED. No external deployment
or security/load audit was performed. See [milestone 01](milestones/01.md).
