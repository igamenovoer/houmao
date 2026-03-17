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
POSITIONAL_ARGS=()

print_help() {
  cat <<'EOF'
Usage:
  scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh [auto|start|roundtrip|verify|stop] [--snapshot-report] [--demo-output-dir <path>] [--jobs-dir <path>]
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

DEMO_OUTPUT_DIR="$(resolve_path "$RAW_DEMO_OUTPUT_DIR" "tmp/demo/mailbox-roundtrip-tutorial-pack")"
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
