#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
HELPER_SCRIPT="$SCRIPT_DIR/scripts/stalwart_demo_helpers.py"
PARAMETERS_PATH="$SCRIPT_DIR/inputs/demo_parameters.json"

COMMAND="start"
RAW_DEMO_OUTPUT_DIR=""
POSITIONAL_ARGS=()

print_help() {
  cat <<'EOF'
Usage:
  scripts/demo/gateway-stalwart-cypht-interactive-demo-pack/run_demo.sh [start|send|reply|check|watch|inspect|stop] [--demo-output-dir <path>] [command args...]
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    start|send|reply|check|watch|inspect|stop)
      COMMAND="$1"
      shift
      ;;
    --demo-output-dir)
      [[ $# -ge 2 ]] || {
        echo "--demo-output-dir requires a value" >&2
        exit 1
      }
      RAW_DEMO_OUTPUT_DIR="$2"
      shift 2
      ;;
    -h|--help)
      print_help
      exit 0
      ;;
    *)
      POSITIONAL_ARGS+=("$1")
      shift
      ;;
  esac
done

resolve_path() {
  local raw_path="${1:-}"
  local default_relative="${2:-}"
  local args=(pixi run python "$HELPER_SCRIPT" resolve-path --repo-root "$REPO_ROOT")
  if [[ -n "$default_relative" ]]; then
    args+=(--default-relative "$default_relative")
  fi
  if [[ -n "$raw_path" ]]; then
    args+=("$raw_path")
  fi
  "${args[@]}"
}

if ! command -v pixi >/dev/null 2>&1; then
  echo "pixi not found on PATH" >&2
  exit 1
fi

DEMO_OUTPUT_DIR="$(resolve_path "$RAW_DEMO_OUTPUT_DIR" "tmp/demo/gateway-stalwart-cypht-interactive-demo-pack")"

pixi run python "$HELPER_SCRIPT" "$COMMAND" \
  --repo-root "$REPO_ROOT" \
  --pack-dir "$SCRIPT_DIR" \
  --parameters "$PARAMETERS_PATH" \
  --demo-output-dir "$DEMO_OUTPUT_DIR" \
  "${POSITIONAL_ARGS[@]}"
