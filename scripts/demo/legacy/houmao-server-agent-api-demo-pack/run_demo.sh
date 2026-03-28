#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELPER_SCRIPT="$SCRIPT_DIR/scripts/demo_pack_helpers.py"

if ! command -v pixi >/dev/null 2>&1; then
  echo "pixi not found on PATH" >&2
  exit 1
fi

exec pixi run python "$HELPER_SCRIPT" "$@"
