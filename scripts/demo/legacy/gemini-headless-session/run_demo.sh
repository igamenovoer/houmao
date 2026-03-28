#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
AGENT_DEF_DIR="${AGENT_DEF_DIR:-$REPO_ROOT/tests/fixtures/agents}"
WORKSPACE_DIR="$REPO_ROOT/tmp/demo_gemini_headless_$(date +%Y%m%d_%H%M%S)_$$"
RUNTIME_ROOT="$WORKSPACE_DIR/runtime"
REPORT_PATH="$WORKSPACE_DIR/report.json"
DEMO_TIMEOUT_SECONDS="${DEMO_TIMEOUT_SECONDS:-180}"
SNAPSHOT=0
if [[ "${1:-}" == "--snapshot-report" ]]; then
  SNAPSHOT=1
fi

log() {
  echo "[demo][gemini-headless] $*"
}

skip() {
  log "SKIP: $*"
  exit 0
}

fail() {
  log "FAIL: $*"
  exit 1
}

classify_skip_reason() {
  local log_path="$1"
  if grep -Eiq "Missing credential profile|Missing credential env file|Missing file|oauth_creds.json|Please set an Auth method|GEMINI_API_KEY|GOOGLE_GENAI_USE_VERTEXAI|GOOGLE_GENAI_USE_GCA" "$log_path"; then
    echo "missing credentials"
    return 0
  fi
  if grep -Eiq "401|403|unauthori[sz]ed|forbidden|invalid api key|authentication" "$log_path"; then
    echo "invalid credentials"
    return 0
  fi
  if grep -Eiq "Connection refused|timed out|timeout|network is unreachable|Name or service not known|Temporary failure" "$log_path"; then
    echo "connectivity unavailable"
    return 0
  fi
  return 1
}

run_cmd() {
  local label="$1"
  shift
  local log_path="$WORKSPACE_DIR/${label}.log"
  local exit_code=0
  if timeout "$DEMO_TIMEOUT_SECONDS" "$@" >"$log_path" 2>&1; then
    return 0
  else
    exit_code=$?
  fi
  if [[ "$exit_code" -eq 124 || "$exit_code" -eq 137 || "$exit_code" -eq 143 ]]; then
    skip "connectivity unavailable or command timed out after ${DEMO_TIMEOUT_SECONDS}s (see $log_path)"
  fi
  if reason="$(classify_skip_reason "$log_path")"; then
    skip "$reason (see $log_path)"
  fi
  fail "command failed: ${label} (see $log_path)"
}

extract_json_field() {
  local json_path="$1"
  local field_name="$2"
  pixi run python - "$json_path" "$field_name" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
print(payload[sys.argv[2]])
PY
}

extract_response_text() {
  local events_path="$1"
  pixi run python - "$events_path" <<'PY'
import json
import sys
from pathlib import Path

lines = [line.strip() for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines() if line.strip()]
response = ""
for line in lines:
    event = json.loads(line)
    if event.get("kind") == "done":
        response = str(event.get("message", ""))
print(response)
PY
}

mkdir -p "$WORKSPACE_DIR"
log "workspace: $WORKSPACE_DIR"
log "using allowlisted env names: GOOGLE_API_KEY GEMINI_API_KEY GOOGLE_GENAI_USE_VERTEXAI"

if [[ ! -f "$AGENT_DEF_DIR/brains/api-creds/gemini/personal-a-default/env/vars.env" ]]; then
  skip "missing credential env file for gemini profile personal-a-default"
fi
if [[ ! -f "$AGENT_DEF_DIR/brains/api-creds/gemini/personal-a-default/files/oauth_creds.json" ]]; then
  skip "missing oauth_creds.json for gemini profile personal-a-default"
fi

cp "$SCRIPT_DIR/inputs/prompt.txt" "$WORKSPACE_DIR/prompt.txt"
PROMPT="$(<"$WORKSPACE_DIR/prompt.txt")"

run_cmd build pixi run python -m houmao.agents.realm_controller build-brain \
  --agent-def-dir "$AGENT_DEF_DIR" \
  --runtime-root "$RUNTIME_ROOT" \
  --tool gemini \
  --skill openspec-apply-change \
  --config-profile default \
  --cred-profile personal-a-default

MANIFEST_PATH="$(extract_json_field "$WORKSPACE_DIR/build.log" manifest_path)"

run_cmd start pixi run python -m houmao.agents.realm_controller start-session \
  --agent-def-dir "$AGENT_DEF_DIR" \
  --runtime-root "$RUNTIME_ROOT" \
  --brain-manifest "$MANIFEST_PATH" \
  --role gpu-kernel-coder \
  --backend gemini_headless \
  --workdir "$WORKSPACE_DIR"

SESSION_MANIFEST="$(extract_json_field "$WORKSPACE_DIR/start.log" session_manifest)"

run_cmd prompt pixi run python -m houmao.agents.realm_controller send-prompt \
  --agent-def-dir "$AGENT_DEF_DIR" \
  --agent-identity "$SESSION_MANIFEST" \
  --prompt "$PROMPT"

RESPONSE_TEXT="$(extract_response_text "$WORKSPACE_DIR/prompt.log")"
if [[ -z "${RESPONSE_TEXT// }" ]]; then
  fail "prompt response was empty"
fi

pixi run python -m houmao.agents.realm_controller stop-session \
  --agent-def-dir "$AGENT_DEF_DIR" \
  --agent-identity "$SESSION_MANIFEST" >"$WORKSPACE_DIR/stop.log" 2>&1 || true

pixi run python - "$REPORT_PATH" "$SESSION_MANIFEST" "$WORKSPACE_DIR" "$RESPONSE_TEXT" <<'PY'
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

report_path = Path(sys.argv[1])
session_manifest = sys.argv[2]
workspace = sys.argv[3]
response_text = sys.argv[4]
payload = {
    "status": "ok",
    "backend": "gemini_headless",
    "tool": "gemini",
    "response_text": response_text,
    "session_manifest": session_manifest,
    "workspace": workspace,
    "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
}
report_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

VERIFY_SCRIPT="$SCRIPT_DIR/scripts/verify_report.py"
EXPECTED_REPORT="$SCRIPT_DIR/expected_report/report.json"

pixi run python "$VERIFY_SCRIPT" "$REPORT_PATH" "$EXPECTED_REPORT"

if [[ "$SNAPSHOT" -eq 1 ]]; then
  pixi run python "$VERIFY_SCRIPT" --snapshot "$REPORT_PATH" "$EXPECTED_REPORT"
fi

log "demo complete"
log "report: $REPORT_PATH"
