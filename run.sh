#!/usr/bin/env bash
# One-command demo: creates .venv if needed, installs light deps, starts Shot Director in DEMO mode (no keys).
set -euo pipefail
cd "$(dirname "$0")"
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
  echo "Shot Director needs Python 3.10+ (found: $(python3 --version 2>&1 || echo none))." >&2; exit 1
fi
if ! command -v ffmpeg >/dev/null 2>&1; then echo "Note: ffmpeg not found on PATH; clips and sequences need it." >&2; fi
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
  .venv/bin/python -m pip install -q -U pip
  .venv/bin/python -m pip install -q -r requirements.txt
fi
export DEMO="${DEMO:-1}"
exec .venv/bin/python -m app.server
