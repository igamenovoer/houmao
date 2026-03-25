#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

show_usage() {
  cat <<EOF
Usage:
  $(basename "$0") [-y] [--provider <claude_code|codex>] [--help]

Launch or replace the interactive session with the fixed demo session-name
\`alice\`. The pair-managed launch resolves that to the CAO-compatible
\`cao-alice\` session while the demo keeps the operator-facing override stable.

Delegates to:
  $SCRIPT_DIR/run_demo.sh [-y] start --session-name alice [--provider <provider>]
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  show_usage
  exit 0
fi

YES_ARGS=()
PROVIDER_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -y|--yes)
      YES_ARGS+=("$1")
      shift
      ;;
    --provider)
      if [[ $# -lt 2 ]]; then
        show_usage >&2
        exit 2
      fi
      PROVIDER_ARGS+=("$1" "$2")
      shift 2
      ;;
    *)
      show_usage >&2
      exit 2
      ;;
  esac
done

exec "$SCRIPT_DIR/run_demo.sh" "${YES_ARGS[@]}" start --session-name alice "${PROVIDER_ARGS[@]}"
