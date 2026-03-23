#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./helpers/common.sh
source "$SCRIPT_DIR/helpers/common.sh"

CASE_ID="unattended-full-run"
OUTPUT_ROOT="$(resolve_demo_output_root "$@")"
STATE_PATH="$(state_path_from_output_root "$OUTPUT_ROOT")"
INSPECT_PATH="$(inspect_path_from_output_root "$OUTPUT_ROOT")"
RESULT_PATH="$(result_path_from_output_root "$OUTPUT_ROOT" "$CASE_ID")"

CASE_STATUS="failed"
FAILURE_REASON="case exited before completion"
RUN_STARTED=0
STOP_COMPLETED=0
declare -a SNAPSHOT_PATHS=()

finalize_case() {
    local exit_code="$1"

    if [[ "$RUN_STARTED" -eq 1 && "$CASE_STATUS" != "passed" ]]; then
        if [[ -f "$STATE_PATH" ]]; then
            mapfile -t _failure_snapshots < <(capture_tmux_snapshots "$OUTPUT_ROOT" "failure" 120)
            SNAPSHOT_PATHS+=("${_failure_snapshots[@]}")
            run_pack inspect --demo-output-dir "$OUTPUT_ROOT" >/dev/null 2>&1 || true
            if [[ "$STOP_COMPLETED" -eq 0 ]]; then
                run_pack stop --demo-output-dir "$OUTPUT_ROOT" >/dev/null 2>&1 || true
                STOP_COMPLETED=1
            fi
        fi
    fi

    local -a result_args=(
        --case-id "$CASE_ID"
        --status "$CASE_STATUS"
        --failure-reason "$FAILURE_REASON"
        --output-root "$OUTPUT_ROOT"
        --result-path "$RESULT_PATH"
    )
    local snapshot_path
    for snapshot_path in "${SNAPSHOT_PATHS[@]}"; do
        result_args+=(--snapshot-path "$snapshot_path")
    done

    if ! write_case_result "${result_args[@]}"; then
        echo "failed to write case result: $RESULT_PATH" >&2
    fi

    exit "$exit_code"
}

trap 'finalize_case "$?"' EXIT

echo "== Running unattended full-run autotest case =="
echo "repo_root: $REPO_ROOT"
echo "demo_output_root: $OUTPUT_ROOT"
echo

FAILURE_REASON="preflight failed"
preflight

FAILURE_REASON="could not prepare a fresh output root"
prepare_fresh_output_root "$OUTPUT_ROOT"

FAILURE_REASON="demo start failed"
run_pack start --demo-output-dir "$OUTPUT_ROOT"
RUN_STARTED=1
echo
pixi run python "$STATE_SUMMARY_HELPER" "$STATE_PATH"

FAILURE_REASON="launch posture inspection failed after start"
run_pack inspect --demo-output-dir "$OUTPUT_ROOT"
pixi run python "$LAUNCH_POSTURE_HELPER" "$INSPECT_PATH"
mapfile -t _start_snapshots < <(capture_tmux_snapshots "$OUTPUT_ROOT" "after-start" 80)
SNAPSHOT_PATHS+=("${_start_snapshots[@]}")

FAILURE_REASON="kickoff failed"
run_pack kickoff --demo-output-dir "$OUTPUT_ROOT"
mapfile -t _kickoff_snapshots < <(capture_tmux_snapshots "$OUTPUT_ROOT" "after-kickoff" 120)
SNAPSHOT_PATHS+=("${_kickoff_snapshots[@]}")

FAILURE_REASON="bounded wait failed"
run_pack wait --demo-output-dir "$OUTPUT_ROOT"

FAILURE_REASON="inspect or launch posture validation failed after wait"
run_pack inspect --demo-output-dir "$OUTPUT_ROOT"
pixi run python "$LAUNCH_POSTURE_HELPER" "$INSPECT_PATH"

FAILURE_REASON="verification failed"
run_pack verify --demo-output-dir "$OUTPUT_ROOT"

FAILURE_REASON="stop failed"
run_pack stop --demo-output-dir "$OUTPUT_ROOT"
STOP_COMPLETED=1

CASE_STATUS="passed"
FAILURE_REASON=""
echo
echo "Case complete."
echo "result_path: $RESULT_PATH"
