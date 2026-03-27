#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/helpers/common.sh"

RESULT_PATH="$AUTOTEST_CONTROL_DIR/case-real-agent-interrupt-recovery.result.json"
INTERRUPT_PROMPT="$AUTOTEST_PACK_DIR/inputs/interrupt_prompt.txt"
STOP_REQUESTED=0

cleanup() {
  if [[ "$STOP_REQUESTED" -eq 0 ]]; then
    best_effort_stop_demo "99-stop-recovery"
  fi
}

ensure_case_dirs
trap cleanup EXIT

run_logged_command "01-start" "$AUTOTEST_RUN_DEMO_SCRIPT" start --demo-output-dir "$AUTOTEST_DEMO_OUTPUT_DIR" --lane claude-tui --lane codex-headless
run_logged_command "02-inspect-before-interrupt" "$AUTOTEST_RUN_DEMO_SCRIPT" inspect --demo-output-dir "$AUTOTEST_DEMO_OUTPUT_DIR" --lane claude-tui --lane codex-headless
run_logged_command "03-prompt" "$AUTOTEST_RUN_DEMO_SCRIPT" prompt --demo-output-dir "$AUTOTEST_DEMO_OUTPUT_DIR" --lane claude-tui --lane codex-headless --prompt-file "$INTERRUPT_PROMPT"
run_logged_command "04-interrupt" "$AUTOTEST_RUN_DEMO_SCRIPT" interrupt --demo-output-dir "$AUTOTEST_DEMO_OUTPUT_DIR" --lane claude-tui --lane codex-headless
run_logged_command "05-inspect-after-interrupt" "$AUTOTEST_RUN_DEMO_SCRIPT" inspect --demo-output-dir "$AUTOTEST_DEMO_OUTPUT_DIR" --lane claude-tui --lane codex-headless --with-dialog-tail 400
run_logged_command "06-stop" "$AUTOTEST_RUN_DEMO_SCRIPT" stop --demo-output-dir "$AUTOTEST_DEMO_OUTPUT_DIR"
STOP_REQUESTED=1
trap - EXIT
write_result_json "$RESULT_PATH" "real-agent-interrupt-recovery" "passed" "$AUTOTEST_DEMO_OUTPUT_DIR"
