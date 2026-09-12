# Source and dependency map — audit 00

Inspected HEAD/reference: `8748e5bd30794d14afeb3441904221b52a002cac`.
No initial tracked changes; the preexisting `flytrap-kit/` directory was untracked.
No on-disk AGENTS.md, parent AGENTS.md, CLAUDE.md, CONTRIBUTING guide, or CI workflow
was found. The user-supplied instructions are preserved in root AGENTS.md.
README, license/notices, kit PLAN/BOUNDARIES, and prompt 00 were read. Other numbered
prompts were not executed; their bytes were only hashed for kit preservation.

Configured remotes (local configuration inspected; no remote contacted):
`origin=https://github.com/beetee2/flycoinrh.git` and
`upstream=https://github.com/fruitflydev/flycoinrh.git`, each for fetch and push.

| Source | Verified role / finding | Later integration obligation |
|---|---|---|
| `build_graph.py:41-117` | Feather weights/annotations/transmitters → sparse graph. Filters weight ≥3 before endpoint filtering and duplicate aggregation; keeps sorted traced non-glial bodies. NT and annotation duplicates use first occurrence. | Test ordering, threshold, body mapping, deduplication, missing/corrupt input. Dense ID validity mask and empty-input assumptions need bounded handling. |
| `build_graph.py:24-34,97-117` | `W[post,pre]`; presynaptic sign multiplies synapse counts. Dopamine/octopamine/serotonin and unknown/unclear zero weights are dropped. Output has per-neuron metadata but no anatomical count matrix. | Retain anatomical counts before signs. A transpose cannot reconstruct removed edges. |
| `flysim.py:35-64,96-102,165-174` | Explicit graph path supported. Converts CSR to CSC and propagates from presynaptic columns. Every run creates RNG, resting membrane, and zero refractory arrays. | Preserve named `windowed_reset`; validate populations and numeric bounds; prove determinism in locked runtime. |
| `flyeye.py:16-18,54-77,93-116` | Eye annotation default is CWD-relative; pilot reads the same hardcoded path even with injected eye. Sampling uses 300×210 field, integer truncation and clipping. | Inject both paths; regression-test cropped observation parity including edges. |
| `flyeye.py:119-165` | Movement from DNa02/DNa01/MDN/DNp09 rates, clipped/scaled to 90 pixels; click uses stop activity while recorded `click` population is MN9. Empty motor means can become NaN. | Validate required populations and finite output; declare action/click mapping and telemetry. |
| `mushroom.py:67-78` | `W[pam][:,mbon]` reads MBON→PAM under verified orientation, despite describing incoming PAM connectivity. Ties/zero totals remain unclassified. | Correct direction using retained anatomy; keep uncertain labels explicit; test on hand-computed graph. |
| `mushroom.py:43-47,94-100,163-194` | Constructor calls load; `FLY_STATE_DIR/mb_gains.npz` or `build/mb_gains.npz` fallback. Checks length/positions only, applies loaded gain, swallows save/load errors. | Explicit baseline/checkpoint choice; immutable graph/mapping validation; finite bounded gains; atomic persistence. |
| `calibration.py:64-95,113-125` | Stored upstream summaries and CHOSEN preset; per-type gains for APL/ORN/PN/KC, including thermo/hygrosensory PN types. Positive infinity is not rejected. | Treat values as experimental conditions, not local measurements. No runtime CHOSEN use found outside tests. |
| `olfaction.py`, `door/` | DoOR CSV reader and receptor drive; chosen coin-to-odor convention. Bundled data used by offline tests. | Outside the core vision-only controller; preserve separate data attribution if reused. |
| `roam.py`, `web/roam.html` | Browser-driven web roaming, mutable learning, websocket telemetry. Public tunnel/address publication and blob operations exist. | Do not reuse as FLYTRAP entrypoint or source of authoritative challenge outcomes. |
| `rhlive.py`, `web/live.html` | Wallet-capable launch rig, scripted UI completion, implicit `build/gains_ui.npz` load at 582-589. | Outside FLYTRAP control path. Preserve upstream files. |
| `rhwallet.py`, `rhprovider.py`, `rhdryrun.py`, `pons.py`, `check_wallet.py`, `probe_adv.py` | Wallet/account, provider, RPC/signing/launch/trade or related probes; pons builds unsigned transaction data. | No FLYTRAP imports or execution of these entrypoints. Offline pons tests remain upstream regression coverage. |
| `voice.py`, `xpost.py`, `voice_prompt.md`, `disclosure.md`, `envcfg.py` | Narrator, X publishing and environment loader; imports can read `.env` through config. | Keep narrator/credentials outside model and app paths. Existing tests mock network/publication. |
| `Dockerfile`, `.dockerignore` | `python:3.12-slim`; installs roam requirements and Chromium; copies data/build and all root Python files; starts `roam.py`; no USER. | Future dedicated pinned nonroot FLYTRAP container. Source checkout lacks copied model data. |
| `run_all.py` | Alternate supervisor for roamer plus optional voice; not current Docker CMD. | Do not mistake it for the specified durable worker. |
| `site/server/main.py`, Procfile, Railway config | Chain-reading FastAPI service launched with `uvicorn main:app`; wildcard read CORS. | Existing service is not FLYTRAP API. |
| `site/api/state.js`, `site/web/`, `site/vercel.json` | Chain proxy/static site and Vercel output configuration. | Separate from planned same-origin challenge/replay UI. |
| `record.py`, `assets/` | Upstream recorder and visual/gain assets. `assets/gains_ui.npz` exists but no runtime build checkpoint exists. | Hash and explicitly select any reused model asset; do not label old output as FLYTRAP evidence. |

Required model files are absent: `data/connectome-weights.feather`,
`data/body-neurotransmitters.feather`, `data/body-annotations.feather`, and
`build/graph.npz`. README names versioned upstream downloads that must be mapped to
these local filenames. Acquisition/build/checksum validation is still outstanding.
No external asset or model-statistic verification was performed.

| Dependency group | Repository declaration | Observed host / gap |
|---|---|---|
| Python | Docker 3.12 floating tag; site runtime `python-3.12`; no runtime lock | `/usr/bin/python` 3.14.7; compatibility with full pins not established. |
| Numerical/data | NumPy 2.4.2, SciPy 1.17.1, pandas 3.0.1, PyArrow 23.0.1 | NumPy 2.5.3; other three absent. |
| HTTP/images | requests 2.32.5, Pillow 12.2.0 | requests 2.34.2, Pillow 12.3.0. |
| API | FastAPI 0.128.0, uvicorn[standard] 0.40.0 | FastAPI absent; uvicorn 0.52.4, Pydantic 2.13.5. Site separately pins older FastAPI/uvicorn/requests. |
| Browser | Playwright 1.62.0 plus separate Chromium installation | Python Playwright/CLI absent; cached Chromium executable reports 151.0.7922.34. Version probe only; no browser journey validated. |
| Chain | eth-account 0.13.7, eth-utils 5.3.1, eth-abi ≥5,<7 | All absent; eth_abi blocks upstream pons test import. These are outside core dependencies. |
| Testing | Five unittest files; no dev lock/harness | pytest 9.1.1, HTTPX 0.28.1 installed; Hypothesis absent. No FLYTRAP test suite. |
| Frontend | No package.json, lock, TS/React build or tests | Node 26.8.2, npm 12.0.2 installed, not project-validated. |
| Storage/tools | No database/migrations/doctor | Python-linked SQLite 3.53.4 meets kit minimum; uv 0.10.9; Docker CLI 29.7.2; make/git/rg available. Docker daemon/build not tested. |

`requirements.txt` and `requirements-roam.txt` are direct pins, not complete
transitive locks. No dependency installation/resolution was attempted in audit 00.
The foundation milestone must validate actual installability and lock the selected
runtime/dependencies. Host probes report 20 logical CPUs, about 31 GiB total memory
and about 15 GiB available, with about 622 GiB disk free at capture time; these are
capacity observations, not model throughput measurements.

The five files contain 150 test methods by static AST count: calibration 11,
olfaction 11, pons 29, voice 49, X 50. Execution passed all 121 importable methods;
the pons module generated one loader error. Calibration tests check fixture logic
and stored summaries; olfaction tests use real bundled DoOR CSVs with a fake brain;
voice/X tests use stubs and temporary files. None validates real connectome dynamics,
durable FLYTRAP state, browser integration, or visual learning.

Preserved attribution: root MIT [LICENSE](../../LICENSE) and [NOTICE](../../NOTICE)
identify the separately licensed connectome; [door/NOTICE.md](../../door/NOTICE.md)
identifies DoOR's CC BY-SA 4.0 data. No licensing claims were independently audited.
