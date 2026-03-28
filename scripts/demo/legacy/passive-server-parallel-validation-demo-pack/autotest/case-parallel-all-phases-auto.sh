#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=helpers/common.sh
source "$SCRIPT_DIR/helpers/common.sh"

RESULT_PATH="$AUTOTEST_CONTROL_DIR/case-parallel-all-phases-auto.result.json"
ensure_case_dirs

if run_logged_command \
  "01-auto" \
  "$AUTOTEST_RUN_DEMO_SCRIPT" auto \
  --demo-output-dir "$AUTOTEST_DEMO_OUTPUT_DIR" \
  --expected-report "$AUTOTEST_EXPECTED_REPORT"; then
  write_result_json "$RESULT_PATH" "parallel-all-phases-auto" "passed" "$AUTOTEST_DEMO_OUTPUT_DIR"
else
  best_effort_stop_demo
  write_result_json "$RESULT_PATH" "parallel-all-phases-auto" "failed" "$AUTOTEST_DEMO_OUTPUT_DIR" "auto command failed"
  exit 1
fi
