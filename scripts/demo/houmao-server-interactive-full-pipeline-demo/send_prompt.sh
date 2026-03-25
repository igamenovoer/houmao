#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

show_usage() {
  cat <<EOF
Usage:
  $(basename "$0") [-y] --prompt <text>

Send one inline prompt through the active Houmao-server interactive demo
session. \`-y\` is accepted as part of the demo-wide compatibility wrapper
contract.

Delegates to:
  $SCRIPT_DIR/run_demo.sh [-y] send-turn --prompt <text>
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  show_usage
  exit 0
fi

YES_ARGS=()
PROMPT_TEXT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    -y|--yes)
      YES_ARGS+=("$1")
      shift
      ;;
    --prompt)
      if [[ $# -lt 2 ]]; then
        show_usage >&2
        exit 2
      fi
      PROMPT_TEXT="$2"
      shift 2
      ;;
    *)
      show_usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$PROMPT_TEXT" ]]; then
  show_usage >&2
  exit 2
fi

exec "$SCRIPT_DIR/run_demo.sh" "${YES_ARGS[@]}" send-turn --prompt "$PROMPT_TEXT"
