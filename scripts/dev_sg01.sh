#!/usr/bin/env bash
# Art review — capture-only demo and saved replays.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
exec .venv/bin/python -m scripts.sg01_dev "$@" --profile review
