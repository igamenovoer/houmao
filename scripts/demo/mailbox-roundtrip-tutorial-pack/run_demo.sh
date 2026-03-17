#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
HELPER_SCRIPT="$SCRIPT_DIR/scripts/tutorial_pack_helpers.py"
PARAMETERS_PATH="$SCRIPT_DIR/inputs/demo_parameters.json"
EXPECTED_REPORT="$SCRIPT_DIR/expected_report/report.json"

COMMAND="auto"
SNAPSHOT=0
RAW_DEMO_OUTPUT_DIR=""
RAW_JOBS_DIR=""
RAW_PARAMETERS_PATH=""
RAW_EXPECTED_REPORT=""
RAW_CAO_PARSING_MODE=""
POSITIONAL_ARGS=()

print_help() {
  cat <<'EOF'
Usage:
  scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh [auto|start|roundtrip|verify|stop] [--snapshot-report] [--demo-output-dir <path>] [--jobs-dir <path>] [--parameters <path>] [--expected-report <path>] [--cao-parsing-mode <shadow_only>]

The default output root is `scripts/demo/mailbox-roundtrip-tutorial-pack/outputs/`.
Fresh full runs recreate that output root from scratch; stepwise commands reuse the same selected root.

This tutorial pack only supports shadow_only for both agents.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    auto|start|roundtrip|verify|stop)
      COMMAND="$1"
      shift
      ;;
    --snapshot-report)
      SNAPSHOT=1
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
    --jobs-dir)
      [[ $# -ge 2 ]] || {
        echo "--jobs-dir requires a value" >&2
        exit 1
      }
      RAW_JOBS_DIR="$2"
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
    --cao-parsing-mode)
      [[ $# -ge 2 ]] || {
        echo "--cao-parsing-mode requires a value" >&2
        exit 1
      }
      RAW_CAO_PARSING_MODE="$2"
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

if [[ -n "$RAW_CAO_PARSING_MODE" && "$RAW_CAO_PARSING_MODE" != "shadow_only" ]]; then
  echo "mailbox tutorial pack only supports \`shadow_only\`; received \`$RAW_CAO_PARSING_MODE\`" >&2
  exit 1
fi

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

DEMO_OUTPUT_DIR="$(resolve_path "$RAW_DEMO_OUTPUT_DIR" "scripts/demo/mailbox-roundtrip-tutorial-pack/outputs")"
if [[ -n "$RAW_PARAMETERS_PATH" ]]; then
  PARAMETERS_PATH="$(resolve_path "$RAW_PARAMETERS_PATH")"
else
  PARAMETERS_PATH="$SCRIPT_DIR/inputs/demo_parameters.json"
fi
if [[ -n "$RAW_EXPECTED_REPORT" ]]; then
  EXPECTED_REPORT="$(resolve_path "$RAW_EXPECTED_REPORT")"
fi
BASE_ARGS=(
  --repo-root "$REPO_ROOT"
  --pack-dir "$SCRIPT_DIR"
  --parameters "$PARAMETERS_PATH"
  --demo-output-dir "$DEMO_OUTPUT_DIR"
)

if [[ -n "$RAW_JOBS_DIR" && ( "$COMMAND" == "auto" || "$COMMAND" == "start" ) ]]; then
  JOBS_DIR="$(resolve_path "$RAW_JOBS_DIR")"
  BASE_ARGS+=(--jobs-dir "$JOBS_DIR")
fi
if [[ -n "$RAW_CAO_PARSING_MODE" && ( "$COMMAND" == "auto" || "$COMMAND" == "start" || "$COMMAND" == "roundtrip" || "$COMMAND" == "stop" ) ]]; then
  BASE_ARGS+=(--cao-parsing-mode "$RAW_CAO_PARSING_MODE")
fi

case "$COMMAND" in
  auto|verify)
    CMD=(pixi run python "$HELPER_SCRIPT" "$COMMAND" "${BASE_ARGS[@]}" --expected-report "$EXPECTED_REPORT")
    if [[ "$SNAPSHOT" -eq 1 ]]; then
      CMD+=(--snapshot)
    fi
    CMD+=("${POSITIONAL_ARGS[@]}")
    "${CMD[@]}"
    ;;
  start|roundtrip|stop)
    pixi run python "$HELPER_SCRIPT" "$COMMAND" "${BASE_ARGS[@]}" "${POSITIONAL_ARGS[@]}"
    ;;
  *)
    echo "unknown command: $COMMAND" >&2
    exit 1
    ;;
esac
