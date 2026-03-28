#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=helpers/common.sh
source "$SCRIPT_DIR/helpers/common.sh"

PRECHECK_PATH="$AUTOTEST_CONTROL_DIR/case-parallel-preflight.preflight.json"
RESULT_PATH="$AUTOTEST_CONTROL_DIR/case-parallel-preflight.result.json"
STDOUT_PATH="$AUTOTEST_LOG_DIR/01-preflight.stdout.txt"
STDERR_PATH="$AUTOTEST_LOG_DIR/01-preflight.stderr.txt"
COMMAND_PATH="$AUTOTEST_LOG_DIR/01-preflight.command.txt"

ensure_case_dirs
printf '%s\n' "pixi run python $AUTOTEST_PACK_DIR/scripts/demo_pack_helpers.py preflight --demo-output-dir $AUTOTEST_DEMO_OUTPUT_DIR" >"$COMMAND_PATH"

if pixi run python \
  "$AUTOTEST_PACK_DIR/scripts/demo_pack_helpers.py" \
  preflight \
  --demo-output-dir \
  "$AUTOTEST_DEMO_OUTPUT_DIR" >"$PRECHECK_PATH" 2>"$STDERR_PATH"; then
  cp "$PRECHECK_PATH" "$STDOUT_PATH"
  write_result_json "$RESULT_PATH" "parallel-preflight" "passed" "$AUTOTEST_DEMO_OUTPUT_DIR"
else
  if [[ -f "$PRECHECK_PATH" ]]; then
    cp "$PRECHECK_PATH" "$STDOUT_PATH"
  fi
  write_result_json "$RESULT_PATH" "parallel-preflight" "failed" "$AUTOTEST_DEMO_OUTPUT_DIR" "preflight command failed"
  exit 1
fi
