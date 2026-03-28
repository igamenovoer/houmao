#!/usr/bin/env bash
set -euo pipefail

AUTOTEST_HELPERS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTOTEST_DIR="$(cd "$AUTOTEST_HELPERS_DIR/.." && pwd)"
PACK_DIR="$(cd "$AUTOTEST_DIR/.." && pwd)"
REPO_ROOT="$(cd "$PACK_DIR/../../.." && pwd)"
PACK_SCRIPT="$PACK_DIR/run_demo.sh"
PACK_PARAMETERS="$PACK_DIR/inputs/demo_parameters.json"
DEFAULT_DEMO_OUTPUT_ROOT="$REPO_ROOT/.agent-automation/hacktest/mail-ping-pong-gateway-demo-pack/live/demo-output"
PREFLIGHT_HELPER="$AUTOTEST_HELPERS_DIR/check_demo_preflight.py"
LAUNCH_POSTURE_HELPER="$AUTOTEST_HELPERS_DIR/check_launch_posture.py"
STATE_SUMMARY_HELPER="$AUTOTEST_HELPERS_DIR/print_demo_state_summary.py"
TMUX_SNAPSHOT_HELPER="$AUTOTEST_HELPERS_DIR/print_tmux_role_snapshot.sh"
WRITE_RESULT_HELPER="$AUTOTEST_HELPERS_DIR/write_case_result.py"

require_command() {
    local command_name="$1"
    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "missing required command: $command_name" >&2
        return 1
    fi
}

preflight() {
    require_command pixi
    require_command git
    require_command tmux
    require_command claude
    require_command codex
    if [[ ! -x "$PACK_SCRIPT" ]]; then
        echo "demo pack runner not executable: $PACK_SCRIPT" >&2
        return 1
    fi
    (
        cd "$REPO_ROOT"
        pixi run python "$PREFLIGHT_HELPER" \
            --repo-root "$REPO_ROOT" \
            --parameters "$PACK_PARAMETERS"
    )
}

resolve_demo_output_root() {
    local output_root=""
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --demo-output-dir)
                if [[ $# -lt 2 ]]; then
                    echo "missing value for --demo-output-dir" >&2
                    return 2
                fi
                output_root="$2"
                shift 2
                ;;
            *)
                echo "unknown argument: $1" >&2
                return 2
                ;;
        esac
    done
    if [[ -z "$output_root" ]]; then
        output_root="$DEFAULT_DEMO_OUTPUT_ROOT"
    fi
    printf '%s\n' "$output_root"
}

state_path_from_output_root() {
    local output_root="$1"
    printf '%s/control/demo_state.json\n' "$output_root"
}

inspect_path_from_output_root() {
    local output_root="$1"
    printf '%s/control/inspect.json\n' "$output_root"
}

result_path_from_output_root() {
    local output_root="$1"
    local case_id="$2"
    printf '%s/control/autotest/case-%s.result.json\n' "$output_root" "$case_id"
}

require_demo_state() {
    local output_root="$1"
    local state_path
    state_path="$(state_path_from_output_root "$output_root")"
    if [[ ! -f "$state_path" ]]; then
        echo "demo state not found: $state_path" >&2
        return 1
    fi
}

run_pack() {
    (
        cd "$REPO_ROOT"
        "$PACK_SCRIPT" "$@"
    )
}

prepare_fresh_output_root() {
    local output_root="$1"
    local state_path
    state_path="$(state_path_from_output_root "$output_root")"

    if [[ -f "$state_path" ]]; then
        run_pack stop --demo-output-dir "$output_root" >/dev/null 2>&1 || true
    fi
    if [[ -e "$output_root" ]]; then
        rm -rf "$output_root"
    fi
    mkdir -p "$(dirname "$output_root")"
}

capture_tmux_snapshots() {
    local output_root="$1"
    local label="$2"
    local lines="$3"
    local state_path
    state_path="$(state_path_from_output_root "$output_root")"

    if [[ ! -f "$state_path" ]]; then
        return 0
    fi

    local snapshot_dir="$output_root/control/autotest/tmux"
    mkdir -p "$snapshot_dir"
    local role
    for role in initiator responder; do
        local snapshot_path="$snapshot_dir/${role}-${label}.txt"
        if ! bash "$TMUX_SNAPSHOT_HELPER" "$state_path" "$role" "$lines" >"$snapshot_path" 2>&1; then
            :
        fi
        printf '%s\n' "$snapshot_path"
    done
}

write_case_result() {
    (
        cd "$REPO_ROOT"
        pixi run python "$WRITE_RESULT_HELPER" "$@"
    )
}
