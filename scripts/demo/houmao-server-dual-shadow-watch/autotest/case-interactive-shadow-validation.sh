#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/helpers/common.sh"

RAW_OUTPUT_ROOT=""
CLEANUP=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-root)
      RAW_OUTPUT_ROOT="$2"
      shift 2
      ;;
    --cleanup)
      CLEANUP=1
      shift
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

CASE_ID="case-interactive-shadow-validation"
OUTPUT_ROOT="$(resolve_output_root "$RAW_OUTPUT_ROOT" "tmp/demo/houmao-server-dual-shadow-watch/autotest/$CASE_ID")"
RUN_ROOT="$OUTPUT_ROOT/demo-run"
ARTIFACT_DIR="$OUTPUT_ROOT/artifacts"
RESULT_PATH="$OUTPUT_ROOT/result.json"

rm -rf "$OUTPUT_ROOT"
mkdir -p "$ARTIFACT_DIR"

"$RUN_DEMO_SCRIPT" preflight --run-root "$RUN_ROOT" --json > "$ARTIFACT_DIR/preflight.json"
"$RUN_DEMO_SCRIPT" start --run-root "$RUN_ROOT" --json > "$ARTIFACT_DIR/start.json"

pixi run python - "$ARTIFACT_DIR/start.json" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print("Interactive demo staged.")
for slot, agent in sorted(payload["agents"].items()):
    print(f"{slot}: {agent['attach_command']}")
print(f"monitor: {payload['monitor']['attach_command']}")
print(f"run_root: {payload['run_root']}")
PY

if [[ "$CLEANUP" -eq 1 ]]; then
  "$RUN_DEMO_SCRIPT" stop --run-root "$RUN_ROOT" --json > "$ARTIFACT_DIR/stop.json"
  write_result_json "$RESULT_PATH" "staged_and_cleaned" "interactive case staged and then cleaned up"
  exit 0
fi

write_result_json "$RESULT_PATH" "ready_for_manual" "interactive case staged; follow the markdown guide"
