#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(git -C "$PACK_DIR" rev-parse --show-toplevel)"
HELPER_SCRIPT="$PACK_DIR/scripts/tutorial_pack_helpers.py"
RUN_DEMO="$PACK_DIR/run_demo.sh"

CASE_ID="real-agent-roundtrip"
RAW_DEMO_OUTPUT_DIR=""
RAW_PARAMETERS_PATH=""
RAW_EXPECTED_REPORT=""
RAW_JOBS_DIR=""
RAW_REGISTRY_DIR=""
PHASE_TIMEOUT_SECONDS="300"

print_help() {
  cat <<'EOF'
Usage:
  scripts/demo/mailbox-roundtrip-tutorial-pack/autotest/run_autotest.sh [--case <case-id>] [--demo-output-dir <path>] [--parameters <path>] [--expected-report <path>] [--jobs-dir <path>] [--registry-dir <path>] [--phase-timeout-seconds <seconds>]

Supported cases:
  real-agent-roundtrip
  real-agent-preflight
  real-agent-mailbox-persistence

When --demo-output-dir is omitted, the harness creates a timestamped case-owned root under:
  scripts/demo/mailbox-roundtrip-tutorial-pack/outputs/autotest/
EOF
}

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
    --parameters)
      [[ $# -ge 2 ]] || {
        echo "--parameters requires a value" >&2
        exit 1
      }
      RAW_PARAMETERS_PATH="$2"
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
    --jobs-dir)
      [[ $# -ge 2 ]] || {
        echo "--jobs-dir requires a value" >&2
        exit 1
      }
      RAW_JOBS_DIR="$2"
      shift 2
      ;;
    --registry-dir)
      [[ $# -ge 2 ]] || {
        echo "--registry-dir requires a value" >&2
        exit 1
      }
      RAW_REGISTRY_DIR="$2"
      shift 2
      ;;
    --phase-timeout-seconds)
      [[ $# -ge 2 ]] || {
        echo "--phase-timeout-seconds requires a value" >&2
        exit 1
      }
      PHASE_TIMEOUT_SECONDS="$2"
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
  real-agent-roundtrip|real-agent-preflight|real-agent-mailbox-persistence)
    ;;
  *)
    echo "unsupported case: $CASE_ID" >&2
    exit 1
    ;;
esac

if ! [[ "$PHASE_TIMEOUT_SECONDS" =~ ^[0-9]+$ ]] || [[ "$PHASE_TIMEOUT_SECONDS" -le 0 ]]; then
  echo "--phase-timeout-seconds must be a positive integer" >&2
  exit 1
fi

if [[ -n "$RAW_DEMO_OUTPUT_DIR" ]]; then
  DEMO_OUTPUT_DIR="$(resolve_path "$RAW_DEMO_OUTPUT_DIR")"
else
  STAMP="$(date -u +%Y%m%d-%H%M%SZ)"
  DEMO_OUTPUT_DIR="$(resolve_path "" "scripts/demo/mailbox-roundtrip-tutorial-pack/outputs/autotest/${CASE_ID}-${STAMP}")"
fi

if [[ -n "$RAW_PARAMETERS_PATH" ]]; then
  PARAMETERS_PATH="$(resolve_path "$RAW_PARAMETERS_PATH")"
else
  PARAMETERS_PATH="$PACK_DIR/inputs/demo_parameters.json"
fi

if [[ -n "$RAW_EXPECTED_REPORT" ]]; then
  EXPECTED_REPORT_PATH="$(resolve_path "$RAW_EXPECTED_REPORT")"
else
  EXPECTED_REPORT_PATH="$PACK_DIR/expected_report/report.json"
fi

if [[ -n "$RAW_JOBS_DIR" ]]; then
  JOBS_DIR="$(resolve_path "$RAW_JOBS_DIR")"
else
  JOBS_DIR="$DEMO_OUTPUT_DIR/runtime/jobs"
fi

if [[ -n "$RAW_REGISTRY_DIR" ]]; then
  REGISTRY_DIR="$(resolve_path "$RAW_REGISTRY_DIR")"
else
  REGISTRY_DIR="$DEMO_OUTPUT_DIR/runtime/registry"
fi

CASE_BASENAME="case-${CASE_ID}"
TESTPLAN_DIR="$DEMO_OUTPUT_DIR/control/testplans"
RESULT_PATH="$TESTPLAN_DIR/${CASE_BASENAME}.result.json"
LOG_DIR="$TESTPLAN_DIR/logs/${CASE_BASENAME}"
CASE_SCRIPT="$SCRIPT_DIR/${CASE_BASENAME}.sh"

if [[ ! -x "$CASE_SCRIPT" ]]; then
  echo "case script is missing or not executable: $CASE_SCRIPT" >&2
  exit 1
fi

export AUTOTEST_REPO_ROOT="$REPO_ROOT"
export AUTOTEST_PACK_DIR="$PACK_DIR"
export AUTOTEST_HELPER_SCRIPT="$HELPER_SCRIPT"
export AUTOTEST_RUN_DEMO="$RUN_DEMO"
export AUTOTEST_CASE_ID="$CASE_ID"
export AUTOTEST_CASE_BASENAME="$CASE_BASENAME"
export AUTOTEST_DEMO_OUTPUT_DIR="$DEMO_OUTPUT_DIR"
export AUTOTEST_PARAMETERS_PATH="$PARAMETERS_PATH"
export AUTOTEST_EXPECTED_REPORT_PATH="$EXPECTED_REPORT_PATH"
export AUTOTEST_JOBS_DIR="$JOBS_DIR"
export AUTOTEST_REGISTRY_DIR="$REGISTRY_DIR"
export AUTOTEST_PHASE_TIMEOUT_SECONDS="$PHASE_TIMEOUT_SECONDS"
export AUTOTEST_TESTPLAN_DIR="$TESTPLAN_DIR"
export AUTOTEST_RESULT_PATH="$RESULT_PATH"
export AUTOTEST_LOG_DIR="$LOG_DIR"
export AGENTSYS_GLOBAL_REGISTRY_DIR="$REGISTRY_DIR"

echo "case: $CASE_ID"
echo "demo_output_dir: $DEMO_OUTPUT_DIR"
echo "result_path: $RESULT_PATH"

"$CASE_SCRIPT"

echo "autotest result: $RESULT_PATH"
