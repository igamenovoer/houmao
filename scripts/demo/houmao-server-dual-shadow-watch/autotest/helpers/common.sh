#!/usr/bin/env bash
set -euo pipefail

COMMON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACK_DIR="$(cd "$COMMON_DIR/../.." && pwd)"
REPO_ROOT="$(git -C "$PACK_DIR" rev-parse --show-toplevel)"
RUN_DEMO_SCRIPT="$PACK_DIR/run_demo.sh"

resolve_output_root() {
  local raw_path="${1:-}"
  local default_relative="${2:-}"
  local candidate
  if [[ -n "$raw_path" ]]; then
    candidate="$raw_path"
  else
    candidate="$default_relative"
  fi
  if [[ "$candidate" = /* ]]; then
    printf '%s\n' "$candidate"
    return
  fi
  printf '%s\n' "$REPO_ROOT/$candidate"
}

write_result_json() {
  local path="$1"
  local status="$2"
  local message="$3"
  mkdir -p "$(dirname "$path")"
  pixi run python - "$path" "$status" "$message" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
status = sys.argv[2]
message = sys.argv[3]
path.write_text(
    json.dumps({"status": status, "message": message}, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY
}
