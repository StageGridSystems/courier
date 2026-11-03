#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

# Ubuntu Qt runtime libs tip (install once if the app fails to start):
#   sudo apt-get install -y libxcb-cursor0 libxkbcommon-x11-0 libegl1 libgl1 \
#     libnss3 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libasound2t64

export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:$PYTHONPATH}"
exec python -m courier "$@"
