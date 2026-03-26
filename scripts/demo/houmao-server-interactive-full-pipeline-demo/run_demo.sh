#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
DEMO_BASE_ROOT="$REPO_ROOT/tmp/demo/houmao-server-interactive-full-pipeline-demo"
CURRENT_RUN_ROOT_FILE="$DEMO_BASE_ROOT/current_run_root.txt"
YES_TO_ALL=0
FORWARD_ARGS=()

show_usage() {
  cat <<EOF
Usage:
  $(basename "$0") [-y] <subcommand> [options]

Subcommands:
  start [--provider <claude_code|codex>] [--session-name <name>] [--json]
      Start or replace one local managed-agent session without \`houmao-server\`.
      The default provider is \`claude_code\`. The demo keeps bounded local
      shell/provider readiness budgets and an optional Codex warmup override.
  inspect [--json] [--with-dialog-tail <num-tail-chars>]
      Inspect the persisted demo state plus live local managed-agent / tracked
      terminal state.
  send-turn (--prompt <text> | --prompt-file <path>)
      Submit one prompt through the local managed-agent controller path.
  interrupt
      Submit one interrupt through the local managed-agent controller path.
  verify
      Generate a sanitized \`report.json\` from accepted request artifacts and
      local tracked state evidence.
  stop
      Tear down the active local TUI session and mark local state inactive.

Environment defaults:
  DEMO_WORKSPACE_ROOT=<override>
      If omitted, \`start\` creates a fresh per-run root under:
      $DEMO_BASE_ROOT/<utc-ts>/
      Follow-up commands reuse the current run recorded in:
      $CURRENT_RUN_ROOT_FILE
  DEMO_COMPAT_SHELL_READY_TIMEOUT_SECONDS=<override>
  DEMO_COMPAT_PROVIDER_READY_TIMEOUT_SECONDS=<override>
  DEMO_COMPAT_CODEX_WARMUP_SECONDS=<override>
      Override the bounded local launch-readiness budgets.

Flags:
  -y, --yes
      Accepted as a compatibility no-op to preserve the older demo wrapper
      contract. The local demo pack does not prompt during startup.

Examples:
  $(basename "$0") start
  $(basename "$0") start --provider codex
  $(basename "$0") start --session-name alice
  $(basename "$0") inspect --with-dialog-tail 400
  $(basename "$0") send-turn --prompt "Summarize the current README changes."
  $(basename "$0") interrupt
  $(basename "$0") verify
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
      FORWARD_ARGS+=("$arg")
      ;;
  esac
done

PYTHON_ARGS=(
  pixi run python -m houmao.demo.houmao_server_interactive_full_pipeline_demo.cli
  --repo-root "$REPO_ROOT"
)

if [[ -n "${DEMO_WORKSPACE_ROOT:-}" ]]; then
  PYTHON_ARGS+=(--workspace-root "$DEMO_WORKSPACE_ROOT")
fi
if [[ -n "${DEMO_REQUEST_SETTLE_TIMEOUT_SECONDS:-}" ]]; then
  PYTHON_ARGS+=(--request-settle-timeout-seconds "$DEMO_REQUEST_SETTLE_TIMEOUT_SECONDS")
fi
if [[ -n "${DEMO_REQUEST_POLL_INTERVAL_SECONDS:-}" ]]; then
  PYTHON_ARGS+=(--request-poll-interval-seconds "$DEMO_REQUEST_POLL_INTERVAL_SECONDS")
fi
if [[ -n "${DEMO_COMPAT_SHELL_READY_TIMEOUT_SECONDS:-}" ]]; then
  PYTHON_ARGS+=(--compat-shell-ready-timeout-seconds "$DEMO_COMPAT_SHELL_READY_TIMEOUT_SECONDS")
fi
if [[ -n "${DEMO_COMPAT_PROVIDER_READY_TIMEOUT_SECONDS:-}" ]]; then
  PYTHON_ARGS+=(--compat-provider-ready-timeout-seconds "$DEMO_COMPAT_PROVIDER_READY_TIMEOUT_SECONDS")
fi
if [[ -n "${DEMO_COMPAT_CODEX_WARMUP_SECONDS:-}" ]]; then
  PYTHON_ARGS+=(--compat-codex-warmup-seconds "$DEMO_COMPAT_CODEX_WARMUP_SECONDS")
fi
PYTHON_ARGS+=("${FORWARD_ARGS[@]}")

if [[ "$YES_TO_ALL" -eq 1 ]]; then
  :
fi

exec "${PYTHON_ARGS[@]}"
