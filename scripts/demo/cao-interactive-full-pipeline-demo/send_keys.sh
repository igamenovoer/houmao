#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

show_usage() {
  cat <<EOF
Usage:
  $(basename "$0") [-y] [--as-raw-string] <key-stream>

Send one raw control-input key stream through the active interactive demo
session. Quote <key-stream> when it contains spaces or shell metacharacters.
\`-y\` is accepted as part of the demo-wide yes-to-all wrapper contract.
Use \`--\` before <key-stream> if the string itself begins with a dash.

Delegates to:
  $SCRIPT_DIR/run_demo.sh [-y] send-keys <key-stream> [--as-raw-string]
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  show_usage
  exit 0
fi

YES_ARGS=()
RAW_STRING_ARGS=()
KEY_STREAM=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -y|--yes)
      YES_ARGS+=("$1")
      shift
      ;;
    --as-raw-string)
      RAW_STRING_ARGS+=("$1")
      shift
      ;;
    --)
      shift
      if [[ $# -lt 1 || -n "$KEY_STREAM" ]]; then
        show_usage >&2
        exit 2
      fi
      KEY_STREAM="$1"
      shift
      ;;
    *)
      if [[ -n "$KEY_STREAM" ]]; then
        show_usage >&2
        exit 2
      fi
      KEY_STREAM="$1"
      shift
      ;;
  esac
done

if [[ -z "$KEY_STREAM" ]]; then
  show_usage >&2
  exit 2
fi

exec "$SCRIPT_DIR/run_demo.sh" "${YES_ARGS[@]}" send-keys "$KEY_STREAM" "${RAW_STRING_ARGS[@]}"
