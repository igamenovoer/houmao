#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRIVER_SCRIPT="$SCRIPT_DIR/scripts/demo_driver.py"

if ! command -v pixi >/dev/null 2>&1; then
  echo "pixi not found on PATH" >&2
  exit 1
fi

COMMAND="${1:-auto}"
shift || true

case "$COMMAND" in
  auto|start|drive|inspect|verify|stop)
    exec pixi run python "$DRIVER_SCRIPT" "$COMMAND" "$@"
    ;;
  -h|--help|help)
    exec pixi run python "$DRIVER_SCRIPT" --help
    ;;
  *)
    echo "unknown command: $COMMAND" >&2
    echo "usage: scripts/demo/tui-mail-gateway-demo-pack/run_demo.sh [auto|start|drive|inspect|verify|stop] [args...]" >&2
    exit 1
    ;;
esac

