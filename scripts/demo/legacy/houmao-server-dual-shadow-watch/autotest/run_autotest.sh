#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/helpers/common.sh"

CASE_ID="${1:-all}"
shift || true

case "$CASE_ID" in
  all)
    exec "$SCRIPT_DIR/case-preflight-start-stop.sh" "$@"
    ;;
  case-preflight-start-stop)
    exec "$SCRIPT_DIR/case-preflight-start-stop.sh" "$@"
    ;;
  case-interactive-shadow-validation)
    exec "$SCRIPT_DIR/case-interactive-shadow-validation.sh" "$@"
    ;;
  -h|--help|help)
    cat <<'EOF'
Usage:
  scripts/demo/houmao-server-dual-shadow-watch/autotest/run_autotest.sh [all|case-preflight-start-stop|case-interactive-shadow-validation] [--output-root <path>] [--cleanup]
EOF
    exit 0
    ;;
  *)
    echo "unknown autotest case: $CASE_ID" >&2
    exit 1
    ;;
esac
