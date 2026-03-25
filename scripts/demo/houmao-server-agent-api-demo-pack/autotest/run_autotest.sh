#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(git -C "$PACK_DIR" rev-parse --show-toplevel)"
RUN_DEMO_SCRIPT="$PACK_DIR/run_demo.sh"

CASE_ID="real-agent-all-lanes-auto"
RAW_DEMO_OUTPUT_DIR=""
RAW_EXPECTED_REPORT=""

print_help() {
  cat <<'EOF'
Usage:
  scripts/demo/houmao-server-agent-api-demo-pack/autotest/run_autotest.sh [--case <case-id>] [--demo-output-dir <path>] [--expected-report <path>]

Supported cases:
  real-agent-all-lanes-auto
  real-agent-preflight
  real-agent-interrupt-recovery
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --case)
      [[ $# -ge 2 ]] || {
        echo "--case requires a value" >&2
        exit 1
      }
      CASE_ID="$2"
      shift 2
      ;;
    --demo-output-dir)
      [[ $# -ge 2 ]] || {
        echo "--demo-output-dir requires a value" >&2
        exit 1
      }
      RAW_DEMO_OUTPUT_DIR="$2"
      shift 2
      ;;
    --expected-report)
      [[ $# -ge 2 ]] || {
        echo "--expected-report requires a value" >&2
        exit 1
      }
      RAW_EXPECTED_REPORT="$2"
      shift 2
      ;;
    -h|--help)
      print_help
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      print_help >&2
      exit 1
      ;;
  esac
done

case "$CASE_ID" in
  real-agent-all-lanes-auto|real-agent-preflight|real-agent-interrupt-recovery)
    ;;
  *)
    echo "unsupported case: $CASE_ID" >&2
    exit 1
    ;;
esac

if [[ -n "$RAW_DEMO_OUTPUT_DIR" ]]; then
  DEMO_OUTPUT_DIR="$RAW_DEMO_OUTPUT_DIR"
else
  STAMP="$(date -u +%Y%m%d-%H%M%SZ)"
  DEMO_OUTPUT_DIR="$REPO_ROOT/scripts/demo/houmao-server-agent-api-demo-pack/outputs/autotest/${CASE_ID}-${STAMP}"
fi

if [[ -n "$RAW_EXPECTED_REPORT" ]]; then
  EXPECTED_REPORT="$RAW_EXPECTED_REPORT"
else
  EXPECTED_REPORT="$PACK_DIR/expected_report/report.json"
fi

CASE_SCRIPT="$SCRIPT_DIR/case-${CASE_ID}.sh"
if [[ ! -x "$CASE_SCRIPT" ]]; then
  echo "case script is missing or not executable: $CASE_SCRIPT" >&2
  exit 1
fi

export AUTOTEST_CASE_ID="$CASE_ID"
export AUTOTEST_DEMO_OUTPUT_DIR="$DEMO_OUTPUT_DIR"
export AUTOTEST_EXPECTED_REPORT="$EXPECTED_REPORT"
export AUTOTEST_PACK_DIR="$PACK_DIR"
export AUTOTEST_REPO_ROOT="$REPO_ROOT"
export AUTOTEST_RUN_DEMO_SCRIPT="$RUN_DEMO_SCRIPT"
export AUTOTEST_CONTROL_DIR="$DEMO_OUTPUT_DIR/control/autotest"
export AUTOTEST_LOG_DIR="$DEMO_OUTPUT_DIR/logs/autotest/$CASE_ID"

mkdir -p "$AUTOTEST_CONTROL_DIR" "$AUTOTEST_LOG_DIR"

echo "case: $CASE_ID"
echo "demo_output_dir: $DEMO_OUTPUT_DIR"
echo "expected_report: $EXPECTED_REPORT"

exec "$CASE_SCRIPT"
