#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
DEMO_BASE_ROOT="$REPO_ROOT/tmp/demo/cao-interactive-full-pipeline-demo"
CURRENT_RUN_ROOT_FILE="$DEMO_BASE_ROOT/current_run_root.txt"
DEFAULT_AGENT_DEF_DIR="$REPO_ROOT/tests/fixtures/agents"
DEFAULT_ROLE_NAME="gpu-kernel-coder"
SNAPSHOT_REPORT=0
YES_TO_ALL=0
RAW_FORWARD_ARGS=()
FORWARD_ARGS=()

resolve_workspace_root() {
  if [[ -n "${DEMO_WORKSPACE_ROOT:-}" ]]; then
    printf '%s\n' "$DEMO_WORKSPACE_ROOT"
    return 0
  fi
  if [[ -f "$CURRENT_RUN_ROOT_FILE" ]]; then
    tr -d '\n' <"$CURRENT_RUN_ROOT_FILE"
    return 0
  fi
  return 1
}

show_usage() {
  cat <<EOF
Usage:
  $(basename "$0") [-y] <subcommand> [options]

Subcommands:
  start [--agent-name <name>]
      Start or replace the interactive session.
  send-turn (--prompt <text> | --prompt-file <path>)
      Send one prompt to the active session.
  inspect [--json]
      Show tmux/log inspection commands for the current state.
  verify [--snapshot-report]
      Generate report.json and optionally refresh the tracked snapshot.
  stop
      Stop the active interactive session.

Environment defaults:
  DEMO_WORKSPACE_ROOT=<override>
      If omitted, \`start\` creates a fresh per-run root under:
      $DEMO_BASE_ROOT/<utc-ts>/
      Follow-up commands reuse the current run recorded in:
      $CURRENT_RUN_ROOT_FILE
  AGENT_DEF_DIR=$DEFAULT_AGENT_DEF_DIR
  CAO_LAUNCHER_HOME_DIR=<workspace-root>
  DEMO_WORKDIR=<launcher-home>/wktree
  DEMO_ROLE_NAME=$DEFAULT_ROLE_NAME

Flags:
  -y, --yes
      Assume yes for demo prompts such as replacing an existing local
      \`cao-server\` on http://127.0.0.1:9889.

Examples:
  $(basename "$0") -y start --agent-name alice
  $(basename "$0") inspect
  $(basename "$0") send-turn --prompt "Hello from the demo"
  $(basename "$0") verify --snapshot-report
  $(basename "$0") stop
EOF
}

if [[ $# -eq 0 || "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  show_usage
  exit 0
fi

for arg in "$@"; do
  case "$arg" in
    -y|--yes)
      YES_TO_ALL=1
      ;;
    *)
      RAW_FORWARD_ARGS+=("$arg")
      ;;
  esac
done

if [[ "${RAW_FORWARD_ARGS[0]:-}" == "verify" ]]; then
  for arg in "${RAW_FORWARD_ARGS[@]}"; do
    if [[ "$arg" == "--snapshot-report" ]]; then
      SNAPSHOT_REPORT=1
      continue
    fi
    FORWARD_ARGS+=("$arg")
  done
else
  FORWARD_ARGS=("${RAW_FORWARD_ARGS[@]}")
fi

PYTHON_ARGS=(
  pixi run python -m gig_agents.demo.cao_interactive_full_pipeline_demo
  --repo-root "$REPO_ROOT"
)

if [[ -n "${DEMO_WORKSPACE_ROOT:-}" ]]; then
  PYTHON_ARGS+=(--workspace-root "$DEMO_WORKSPACE_ROOT")
fi
if [[ -n "${AGENT_DEF_DIR:-}" ]]; then
  PYTHON_ARGS+=(--agent-def-dir "$AGENT_DEF_DIR")
fi
if [[ -n "${CAO_LAUNCHER_HOME_DIR:-}" ]]; then
  PYTHON_ARGS+=(--launcher-home-dir "$CAO_LAUNCHER_HOME_DIR")
fi
if [[ -n "${DEMO_WORKDIR:-}" ]]; then
  PYTHON_ARGS+=(--workdir "$DEMO_WORKDIR")
fi
if [[ -n "${DEMO_ROLE_NAME:-}" ]]; then
  PYTHON_ARGS+=(--role-name "$DEMO_ROLE_NAME")
fi
if [[ "$YES_TO_ALL" -eq 1 ]]; then
  PYTHON_ARGS+=(--yes)
fi

"${PYTHON_ARGS[@]}" "${FORWARD_ARGS[@]}"

if [[ "${FORWARD_ARGS[0]:-}" == "verify" ]]; then
  VERIFY_SCRIPT="$SCRIPT_DIR/scripts/verify_report.py"
  EXPECTED_REPORT="$SCRIPT_DIR/expected_report/report.json"
  if ! WORKSPACE_ROOT="$(resolve_workspace_root)"; then
    echo "error: no interactive demo workspace was found for verify." >&2
    exit 2
  fi
  VERIFY_ARGS=("$WORKSPACE_ROOT/report.json" "$EXPECTED_REPORT")
  if [[ "$SNAPSHOT_REPORT" -eq 1 ]]; then
    VERIFY_ARGS+=("--snapshot")
  fi
  pixi run python "$VERIFY_SCRIPT" "${VERIFY_ARGS[@]}"
fi
