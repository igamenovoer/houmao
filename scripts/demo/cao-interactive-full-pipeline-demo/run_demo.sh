#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
WORKSPACE_ROOT="${DEMO_WORKSPACE_ROOT:-$REPO_ROOT/tmp/cao_interactive_full_pipeline_demo}"
AGENT_DEF_DIR="${AGENT_DEF_DIR:-$REPO_ROOT/tests/fixtures/agents}"
LAUNCHER_HOME_DIR="${CAO_LAUNCHER_HOME_DIR:-$WORKSPACE_ROOT}"
ROLE_NAME="${DEMO_ROLE_NAME:-gpu-kernel-coder}"
SNAPSHOT_REPORT=0
FORWARD_ARGS=()

show_usage() {
  cat <<EOF
Usage:
  $(basename "$0") <subcommand> [options]

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
  DEMO_WORKSPACE_ROOT=$WORKSPACE_ROOT
  AGENT_DEF_DIR=$AGENT_DEF_DIR
  CAO_LAUNCHER_HOME_DIR=$LAUNCHER_HOME_DIR
  DEMO_ROLE_NAME=$ROLE_NAME

Examples:
  $(basename "$0") start --agent-name alice
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

if [[ "$1" == "verify" ]]; then
  for arg in "$@"; do
    if [[ "$arg" == "--snapshot-report" ]]; then
      SNAPSHOT_REPORT=1
      continue
    fi
    FORWARD_ARGS+=("$arg")
  done
else
  FORWARD_ARGS=("$@")
fi

pixi run python -m gig_agents.demo.cao_interactive_full_pipeline_demo \
  --repo-root "$REPO_ROOT" \
  --workspace-root "$WORKSPACE_ROOT" \
  --agent-def-dir "$AGENT_DEF_DIR" \
  --launcher-home-dir "$LAUNCHER_HOME_DIR" \
  --workdir "$REPO_ROOT" \
  --role-name "$ROLE_NAME" \
  "${FORWARD_ARGS[@]}"

if [[ "${FORWARD_ARGS[0]:-}" == "verify" ]]; then
  VERIFY_SCRIPT="$SCRIPT_DIR/scripts/verify_report.py"
  EXPECTED_REPORT="$SCRIPT_DIR/expected_report/report.json"
  VERIFY_ARGS=("$WORKSPACE_ROOT/report.json" "$EXPECTED_REPORT")
  if [[ "$SNAPSHOT_REPORT" -eq 1 ]]; then
    VERIFY_ARGS+=("--snapshot")
  fi
  pixi run python "$VERIFY_SCRIPT" "${VERIFY_ARGS[@]}"
fi
