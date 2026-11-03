#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install -e ".[build]"
pyinstaller packaging/courier.spec --noconfirm --distpath dist/linux --workpath build/linux
echo "Built dist/linux/Courier"
