#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

show_usage() {
  cat <<EOF
Usage:
  $(basename "$0") [--json] [--with-dialog-tail <num-tail-chars>] [--help]

Inspect the persisted demo state and the live local managed-agent /
tracked-terminal state.

Delegates to:
  $SCRIPT_DIR/run_demo.sh inspect [--json] [--with-dialog-tail <num-tail-chars>]
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  show_usage
  exit 0
fi

exec "$SCRIPT_DIR/run_demo.sh" inspect "$@"
