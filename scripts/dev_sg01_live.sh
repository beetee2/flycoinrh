#!/usr/bin/env bash
# Normal live API in human execution mode; idle until explicit operator control.
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
exec .venv/bin/python -m scripts.sg01_dev "$@" --profile live
