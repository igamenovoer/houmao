#!/usr/bin/env bash
set -euo pipefail

COMMON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACK_DIR="$(cd "$COMMON_DIR/../.." && pwd)"
REPO_ROOT="$(git -C "$PACK_DIR" rev-parse --show-toplevel)"
RUN_DEMO_SCRIPT="$PACK_DIR/run_demo.sh"

ensure_case_dirs() {
  mkdir -p "$AUTOTEST_CONTROL_DIR" "$AUTOTEST_LOG_DIR"
}

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

run_logged_command() {
  local label="$1"
  shift
  local stdout_path="$AUTOTEST_LOG_DIR/${label}.stdout.txt"
  local stderr_path="$AUTOTEST_LOG_DIR/${label}.stderr.txt"
  local command_path="$AUTOTEST_LOG_DIR/${label}.command.txt"
  ensure_case_dirs
  printf '%s\n' "$*" >"$command_path"
  "$@" >"$stdout_path" 2>"$stderr_path"
}

best_effort_stop_demo() {
  local label="${1:-zz-stop-recovery}"
  if [[ ! -x "$AUTOTEST_RUN_DEMO_SCRIPT" ]]; then
    return 0
  fi
  run_logged_command \
    "$label" \
    "$AUTOTEST_RUN_DEMO_SCRIPT" \
    stop \
    --demo-output-dir \
    "$AUTOTEST_DEMO_OUTPUT_DIR" || true
}

write_result_json() {
  local path="$1"
  local case_id="$2"
  local status="$3"
  local output_root="$4"
  local failure_reason="${5:-}"
  mkdir -p "$(dirname "$path")"
  pixi run python - "$path" "$case_id" "$status" "$output_root" "$failure_reason" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1]).resolve()
case_id = sys.argv[2]
status = sys.argv[3]
output_root = Path(sys.argv[4]).resolve()
failure_reason = sys.argv[5].strip() or None
payload = {
    "case_id": case_id,
    "status": status,
    "failure_reason": failure_reason,
    "output_root": str(output_root),
    "artifact_refs": {
        "phase_log_dir": str(output_root / "logs" / "autotest" / case_id),
        "demo_state_path": str(output_root / "control" / "demo_state.json"),
        "report_path": str(output_root / "control" / "report.json"),
        "sanitized_report_path": str(output_root / "control" / "report.sanitized.json"),
        "verify_result_path": str(output_root / "control" / "verify_result.json"),
        "stop_result_path": str(output_root / "control" / "stop_result.json"),
    },
}
path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(path)
PY
}
