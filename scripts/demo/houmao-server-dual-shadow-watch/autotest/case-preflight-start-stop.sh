#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/helpers/common.sh"

RAW_OUTPUT_ROOT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-root)
      RAW_OUTPUT_ROOT="$2"
      shift 2
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

CASE_ID="case-preflight-start-stop"
OUTPUT_ROOT="$(resolve_output_root "$RAW_OUTPUT_ROOT" "tmp/demo/houmao-server-dual-shadow-watch/autotest/$CASE_ID")"
RUN_ROOT="$OUTPUT_ROOT/demo-run"
ARTIFACT_DIR="$OUTPUT_ROOT/artifacts"
RESULT_PATH="$OUTPUT_ROOT/result.json"
CURRENT_STEP="initialization"

rm -rf "$OUTPUT_ROOT"
mkdir -p "$ARTIFACT_DIR"

on_exit() {
  local exit_code="$1"
  if [[ "$exit_code" -eq 0 ]]; then
    write_result_json "$RESULT_PATH" "passed" "preflight/start/inspect/stop completed"
    return
  fi
  write_result_json "$RESULT_PATH" "failed" "failed during $CURRENT_STEP"
}
trap 'on_exit $?' EXIT

CURRENT_STEP="preflight"
"$RUN_DEMO_SCRIPT" preflight --run-root "$RUN_ROOT" --json > "$ARTIFACT_DIR/preflight.json"

CURRENT_STEP="start"
"$RUN_DEMO_SCRIPT" start --run-root "$RUN_ROOT" --json > "$ARTIFACT_DIR/start.json"

CURRENT_STEP="inspect"
"$RUN_DEMO_SCRIPT" inspect --run-root "$RUN_ROOT" --json > "$ARTIFACT_DIR/inspect.json"

CURRENT_STEP="stop"
"$RUN_DEMO_SCRIPT" stop --run-root "$RUN_ROOT" --json > "$ARTIFACT_DIR/stop.json"

CURRENT_STEP="verification"
test -f "$RUN_ROOT/control/preflight.json"
test -f "$RUN_ROOT/monitor/samples.ndjson" || true
test -f "$RUN_ROOT/monitor/transitions.ndjson" || true
