#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

show_usage() {
  cat <<EOF
Usage:
  $(basename "$0") [--help]

Stop the active interactive demo session.

Delegates to:
  $SCRIPT_DIR/run_demo.sh stop
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  show_usage
  exit 0
fi

if [[ $# -ne 0 ]]; then
  show_usage >&2
  exit 2
fi

exec "$SCRIPT_DIR/run_demo.sh" stop
