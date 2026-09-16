#!/usr/bin/env bash
# Safe local art review. Explicit synthetic Preview only; inference is unavailable.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
.venv/bin/python -m scripts.sg01_preview --port 8770 &
sg01_api_pid=$!
trap 'kill "$sg01_api_pid" 2>/dev/null || true' EXIT INT TERM
.venv/bin/python -c 'import time, urllib.request
for attempt in range(50):
    try:
        urllib.request.urlopen("http://127.0.0.1:8770/health/live", timeout=.3)
        break
    except OSError:
        time.sleep(.1)
else:
    raise SystemExit("SG01 safe API failed to become ready")'
kill -0 "$sg01_api_pid"
FLYJAM_API_PORT=8770 npm --prefix web run dev
