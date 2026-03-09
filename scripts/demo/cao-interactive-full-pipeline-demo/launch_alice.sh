#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

show_usage() {
  cat <<EOF
Usage:
  $(basename "$0") [-y] [--help]

Launch or replace the tutorial session as the fixed demo agent \`alice\`.
\`-y\` bypasses confirmation prompts such as replacing an existing local
\`cao-server\` on the demo's fixed loopback target.

Delegates to:
  $SCRIPT_DIR/run_demo.sh [-y] start --agent-name alice
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  show_usage
  exit 0
fi

YES_ARGS=()
for arg in "$@"; do
  case "$arg" in
    -y|--yes)
      YES_ARGS+=("$arg")
      ;;
    *)
      show_usage >&2
      exit 2
      ;;
  esac
done

exec "$SCRIPT_DIR/run_demo.sh" "${YES_ARGS[@]}" start --agent-name alice
