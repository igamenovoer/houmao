#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRIVER_SCRIPT="$SCRIPT_DIR/scripts/demo_driver.py"

if ! command -v pixi >/dev/null 2>&1; then
  echo "pixi not found on PATH" >&2
  exit 1
fi

COMMAND="${1:-help}"
shift || true

case "$COMMAND" in
  recorded-capture|recorded-validate|recorded-validate-corpus|recorded-sweep|start|inspect|stop|cleanup|dashboard)
    exec pixi run python "$DRIVER_SCRIPT" "$COMMAND" "$@"
    ;;
  -h|--help|help)
    exec pixi run python "$DRIVER_SCRIPT" --help
    ;;
  *)
    echo "unknown command: $COMMAND" >&2
    echo "usage: scripts/demo/shared-tui-tracking-demo-pack/run_demo.sh [recorded-capture|recorded-validate|recorded-validate-corpus|recorded-sweep|start|inspect|stop|cleanup|dashboard] [args...]" >&2
    exit 1
    ;;
esac
