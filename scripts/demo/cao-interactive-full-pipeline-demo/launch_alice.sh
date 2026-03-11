#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

show_usage() {
  cat <<EOF
Usage:
  $(basename "$0") [-y] [--brain-recipe <selector>] [--help]

Launch or replace the tutorial session as the fixed demo agent \`alice\`.
\`-y\` bypasses confirmation prompts such as replacing an existing local
\`cao-server\` on the demo's fixed loopback target. Startup progress prints on
stderr and the command ends with a readable summary on stdout.

Delegates to:
  $SCRIPT_DIR/run_demo.sh [-y] start --agent-name alice [--brain-recipe <selector>]
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  show_usage
  exit 0
fi

YES_ARGS=()
BRAIN_RECIPE_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -y|--yes)
      YES_ARGS+=("$1")
      shift
      ;;
    --brain-recipe)
      if [[ $# -lt 2 ]]; then
        show_usage >&2
        exit 2
      fi
      BRAIN_RECIPE_ARGS+=("$1" "$2")
      shift 2
      ;;
    *)
      show_usage >&2
      exit 2
      ;;
  esac
done

exec "$SCRIPT_DIR/run_demo.sh" "${YES_ARGS[@]}" start --agent-name alice "${BRAIN_RECIPE_ARGS[@]}"
