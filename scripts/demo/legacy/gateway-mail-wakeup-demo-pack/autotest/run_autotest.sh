#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(git -C "$PACK_DIR" rev-parse --show-toplevel)"
RUN_DEMO="$PACK_DIR/run_demo.sh"
EXPECTED_REPORT="$PACK_DIR/expected_report/report.json"

CASE_ID="real-agent-both-tools-auto"
RAW_OUTPUT_ROOT=""

print_help() {
  cat <<'EOF'
Usage:
  scripts/demo/gateway-mail-wakeup-demo-pack/autotest/run_autotest.sh [--case <case-id>] [--demo-output-dir <path>]

Cases:
  real-agent-preflight
  real-agent-both-tools-auto
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --case)
      CASE_ID="$2"
      shift 2
      ;;
    --demo-output-dir)
      RAW_OUTPUT_ROOT="$2"
      shift 2
      ;;
    -h|--help)
      print_help
      exit 0
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
if [[ -n "$RAW_OUTPUT_ROOT" ]]; then
  OUTPUT_ROOT="$RAW_OUTPUT_ROOT"
else
  OUTPUT_ROOT="$PACK_DIR/outputs/autotest/${CASE_ID}-${STAMP}"
fi

CONTROL_DIR="$OUTPUT_ROOT/control/autotest"
LOG_DIR="$OUTPUT_ROOT/logs/autotest/$CASE_ID"
mkdir -p "$CONTROL_DIR" "$LOG_DIR"

write_json() {
  local path="$1"
  local payload="$2"
  printf '%s\n' "$payload" >"$path"
}

preflight_json() {
  local status="$1"
  local detail="$2"
  write_json \
    "$CONTROL_DIR/case-${CASE_ID}.preflight.json" \
    "$(cat <<EOF
{
  "case_id": "$CASE_ID",
  "status": "$status",
  "detail": "$detail",
  "output_root": "$OUTPUT_ROOT"
}
EOF
)"
}

result_json() {
  local status="$1"
  local detail="$2"
  write_json \
    "$CONTROL_DIR/case-${CASE_ID}.result.json" \
    "$(cat <<EOF
{
  "case_id": "$CASE_ID",
  "status": "$status",
  "detail": "$detail",
  "output_root": "$OUTPUT_ROOT"
}
EOF
)"
}

check_preflight() {
  if [[ ! -x "$RUN_DEMO" ]]; then
    preflight_json failed "demo runner is not executable"
    result_json failed "demo runner is not executable"
    exit 1
  fi
  if ! command -v pixi >/dev/null 2>&1; then
    preflight_json failed "pixi not found on PATH"
    result_json failed "pixi not found on PATH"
    exit 1
  fi
  if ! command -v tmux >/dev/null 2>&1; then
    preflight_json failed "tmux not found on PATH"
    result_json failed "tmux not found on PATH"
    exit 1
  fi
  if [[ ! -d "$REPO_ROOT/tests/fixtures/agents/brains/api-creds/claude/kimi-coding" ]]; then
    preflight_json failed "missing Claude credential profile kimi-coding"
    result_json failed "missing Claude credential profile kimi-coding"
    exit 1
  fi
  if [[ ! -d "$REPO_ROOT/tests/fixtures/agents/brains/api-creds/codex/yunwu-openai" ]]; then
    preflight_json failed "missing Codex credential profile yunwu-openai"
    result_json failed "missing Codex credential profile yunwu-openai"
    exit 1
  fi
  preflight_json passed "preflight checks passed"
}

check_preflight

case "$CASE_ID" in
  real-agent-preflight)
    result_json passed "preflight checks passed"
    ;;
  real-agent-both-tools-auto)
    set +e
    "$RUN_DEMO" matrix \
      --demo-output-dir "$OUTPUT_ROOT/runs" \
      --expected-report "$EXPECTED_REPORT" \
      >"$LOG_DIR/01-matrix.stdout.txt" \
      2>"$LOG_DIR/01-matrix.stderr.txt"
    STATUS=$?
    set -e
    if [[ "$STATUS" -eq 0 ]]; then
      result_json passed "matrix auto run passed for both tools"
    else
      result_json failed "matrix auto run failed"
      exit "$STATUS"
    fi
    ;;
  *)
    preflight_json failed "unsupported case: $CASE_ID"
    result_json failed "unsupported case: $CASE_ID"
    exit 1
    ;;
esac
