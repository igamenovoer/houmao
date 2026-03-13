#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
AGENT_DEF_DIR="${AGENT_DEF_DIR:-$REPO_ROOT/tests/fixtures/agents}"
WORKSPACE_DIR="$REPO_ROOT/tmp/demo_cao_claude_tmp_write_$(date +%Y%m%d_%H%M%S)_$$"
RUNTIME_ROOT="$WORKSPACE_DIR/runtime"
REPORT_PATH="$WORKSPACE_DIR/report.json"
CAO_BASE_URL="${CAO_BASE_URL:-http://localhost:9889}"
CAO_BASE_URL="${CAO_BASE_URL%/}"
CAO_LAUNCHER_CONFIG_PATH="$WORKSPACE_DIR/cao-server-launcher.toml"
CAO_LAUNCHER_HOME_DIR="${CAO_LAUNCHER_HOME_DIR:-$(dirname "$REPO_ROOT")}"
CAO_PROFILE_STORE="${CAO_PROFILE_STORE:-$CAO_LAUNCHER_HOME_DIR/.aws/cli-agent-orchestrator/agent-store}"
DEMO_TIMEOUT_SECONDS="${DEMO_TIMEOUT_SECONDS:-180}"
OUTPUT_SUBDIR="demo_cao_claude_tmp_write_$(date +%Y%m%d_%H%M%S)_$$"
OUTPUT_FILE_REL="tmp/${OUTPUT_SUBDIR}/hello.py"
OUTPUT_FILE_PATH="$REPO_ROOT/$OUTPUT_FILE_REL"
SENTINEL="CAO_CLAUDE_TMP_WRITE_SENTINEL"
SENTINEL_OUTPUT=""
GIT_DIFF_OUTPUT=""
CAO_SERVER_STARTED=0
SESSION_MANIFEST=""
SESSION_STOPPED=0
SNAPSHOT=0
if [[ "${1:-}" == "--snapshot-report" ]]; then
  SNAPSHOT=1
fi

log() {
  echo "[demo][cao-claude-tmp-write] $*"
}

skip() {
  log "SKIP: $*"
  exit 0
}

fail() {
  log "FAIL: $*"
  exit 1
}

write_cao_launcher_config() {
  mkdir -p "$CAO_LAUNCHER_HOME_DIR"
  cat >"$CAO_LAUNCHER_CONFIG_PATH" <<EOF
base_url = "$CAO_BASE_URL"
runtime_root = "$RUNTIME_ROOT"
home_dir = "$CAO_LAUNCHER_HOME_DIR"
proxy_policy = "clear"
startup_timeout_seconds = 15
EOF
}

parse_launcher_start_state() {
  local output_path="$1"
  pixi run python - "$output_path" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
started = "1" if payload.get("started_new_process") else "0"
reused = "1" if payload.get("reused_existing_process") else "0"
pid = payload.get("pid")
pid_text = "" if pid is None else str(pid)
print(f"{started}:{reused}:{pid_text}")
PY
}

cao_url_is_supported_loopback() {
  [[ "$CAO_BASE_URL" =~ ^http://(localhost|127\.0\.0\.1):[0-9]+$ ]]
}

require_local_cao() {
  if cao_url_is_supported_loopback; then
    return 0
  fi
  skip "local-only demo requires CAO_BASE_URL=http://localhost:<port> or http://127.0.0.1:<port> (got ${CAO_BASE_URL})"
}

ensure_cao_server() {
  write_cao_launcher_config
  log "CAO launcher home: $CAO_LAUNCHER_HOME_DIR"
  log "CAO profile store: $CAO_PROFILE_STORE"

  if ! command -v cao-server >/dev/null 2>&1; then
    skip "CAO server unavailable at ${CAO_BASE_URL} and cao-server not found on PATH"
  fi

  local launcher_status_output_path="$WORKSPACE_DIR/cao-status.json"
  local launcher_status_error_path="$WORKSPACE_DIR/cao-status.err"
  local status_healthy=0
  if pixi run python -m gig_agents.cao.tools.cao_server_launcher status \
    --config "$CAO_LAUNCHER_CONFIG_PATH" >"$launcher_status_output_path" 2>"$launcher_status_error_path"; then
    status_healthy=1
  fi

  if [[ "$status_healthy" -eq 1 ]]; then
    log "CAO server is already healthy at ${CAO_BASE_URL}; verifying launcher ownership via start"
  fi

  local launcher_output_path="$WORKSPACE_DIR/cao-start.json"
  local launcher_error_path="$WORKSPACE_DIR/cao-start.err"
  local launcher_retry_output_path="$WORKSPACE_DIR/cao-start-retry.json"
  local launcher_retry_error_path="$WORKSPACE_DIR/cao-start-retry.err"
  local launcher_stop_output_path="$WORKSPACE_DIR/cao-stop-untracked.json"
  local launcher_stop_error_path="$WORKSPACE_DIR/cao-stop-untracked.err"
  local launcher_state=""
  local started_new_process="0"
  local reused_existing_process="0"
  local resolved_pid=""

  log "starting/attaching CAO server via launcher"
  if ! pixi run python -m gig_agents.cao.tools.cao_server_launcher start \
    --config "$CAO_LAUNCHER_CONFIG_PATH" >"$launcher_output_path" 2>"$launcher_error_path"; then
    skip "CAO connectivity unavailable (launcher start failed, see $launcher_error_path)"
  fi

  launcher_state="$(parse_launcher_start_state "$launcher_output_path")"
  IFS=":" read -r started_new_process reused_existing_process resolved_pid <<<"$launcher_state"
  log "launcher start result: started_new_process=$started_new_process reused_existing_process=$reused_existing_process pid=${resolved_pid:-unknown}"

  if [[ "$reused_existing_process" -eq 1 && -z "$resolved_pid" ]]; then
    log "ownership mismatch: launcher reused untracked CAO server at ${CAO_BASE_URL}"
    log "retrying via launcher stop/start to restore managed context"
    pixi run python -m gig_agents.cao.tools.cao_server_launcher stop \
      --config "$CAO_LAUNCHER_CONFIG_PATH" >"$launcher_stop_output_path" 2>"$launcher_stop_error_path" || true
    if ! pixi run python -m gig_agents.cao.tools.cao_server_launcher start \
      --config "$CAO_LAUNCHER_CONFIG_PATH" >"$launcher_retry_output_path" 2>"$launcher_retry_error_path"; then
      skip "CAO connectivity unavailable (launcher retry failed after ownership mismatch, see $launcher_retry_error_path)"
    fi
    launcher_state="$(parse_launcher_start_state "$launcher_retry_output_path")"
    IFS=":" read -r started_new_process reused_existing_process resolved_pid <<<"$launcher_state"
    log "launcher retry result: started_new_process=$started_new_process reused_existing_process=$reused_existing_process pid=${resolved_pid:-unknown}"
  fi

  if [[ "$reused_existing_process" -eq 1 && -z "$resolved_pid" ]]; then
    skip "CAO server ownership mismatch at ${CAO_BASE_URL}; stop external server and retry (home=${CAO_LAUNCHER_HOME_DIR}, profile_store=${CAO_PROFILE_STORE})"
  fi

  CAO_SERVER_STARTED="$started_new_process"
}

stop_cao_server_if_started() {
  if [[ "$CAO_SERVER_STARTED" -ne 1 ]]; then
    return 0
  fi

  local launcher_output_path="$WORKSPACE_DIR/cao-stop.json"
  local launcher_error_path="$WORKSPACE_DIR/cao-stop.err"
  log "stopping cao-server via launcher"
  pixi run python -m gig_agents.cao.tools.cao_server_launcher stop \
    --config "$CAO_LAUNCHER_CONFIG_PATH" >"$launcher_output_path" 2>"$launcher_error_path" || true
}

cleanup() {
  set +e

  if [[ -n "${SESSION_MANIFEST}" && "$SESSION_STOPPED" -ne 1 ]]; then
    pixi run python -m gig_agents.agents.realm_controller stop-session \
      --agent-def-dir "$AGENT_DEF_DIR" \
      --agent-identity "$SESSION_MANIFEST" >"$WORKSPACE_DIR/stop.log" 2>&1 || true
  fi

  stop_cao_server_if_started
}

classify_skip_reason() {
  local log_path="$1"
  if grep -Eiq "Missing credential profile|Missing credential env file|Missing file" "$log_path"; then
    echo "missing credentials"
    return 0
  fi
  if grep -Eiq "Agent profile not found|Failed to load agent profile" "$log_path"; then
    echo "CAO profile store mismatch"
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

lines = [
    line.strip()
    for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
    if line.strip()
]
response = ""
for line in lines:
    event = json.loads(line)
    if event.get("kind") == "done":
        response = str(event.get("message", ""))
print(response)
PY
}

render_prompt() {
  local template_path="$1"
  local prompt_path="$2"
  pixi run python - "$template_path" "$prompt_path" "$OUTPUT_FILE_REL" "$SENTINEL" <<'PY'
import sys
from pathlib import Path

template_path = Path(sys.argv[1])
prompt_path = Path(sys.argv[2])
output_file_rel = sys.argv[3]
sentinel = sys.argv[4]

prompt_template = template_path.read_text(encoding="utf-8")
rendered = prompt_template.replace("{{OUTPUT_FILE_REL}}", output_file_rel).replace(
    "{{SENTINEL}}", sentinel
)
prompt_path.write_text(rendered, encoding="utf-8")
PY
}

verify_generated_file() {
  if [[ ! -f "$OUTPUT_FILE_PATH" ]]; then
    fail "expected generated file was not created: $OUTPUT_FILE_PATH"
  fi

  local run_stdout_path="$WORKSPACE_DIR/generated_stdout.txt"
  local run_stderr_path="$WORKSPACE_DIR/generated_stderr.txt"
  if ! pixi run python "$OUTPUT_FILE_PATH" >"$run_stdout_path" 2>"$run_stderr_path"; then
    fail "generated file failed to run (see $run_stderr_path)"
  fi

  SENTINEL_OUTPUT="$(<"$run_stdout_path")"
  SENTINEL_OUTPUT="${SENTINEL_OUTPUT%$'\n'}"
  if [[ "$SENTINEL_OUTPUT" != "$SENTINEL" ]]; then
    fail "generated file output mismatch: expected '$SENTINEL', got '$SENTINEL_OUTPUT'"
  fi
}

verify_repo_clean() {
  GIT_DIFF_OUTPUT="$(git -C "$REPO_ROOT" diff --name-only)"
  if [[ -n "${GIT_DIFF_OUTPUT}" ]]; then
    fail "git diff --name-only is not empty after demo: ${GIT_DIFF_OUTPUT//$'\n'/, }"
  fi
}

extract_session_cao_fields() {
  local session_manifest_path="$1"
  pixi run python - "$session_manifest_path" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
cao = payload.get("cao") or {}
session_name = str(cao.get("session_name", "")).strip()
terminal_id = str(cao.get("terminal_id", "")).strip()
if not session_name:
    raise SystemExit("session_name missing in session manifest")
if not terminal_id:
    raise SystemExit("terminal_id missing in session manifest")
print(session_name)
print(terminal_id)
print(f"~/.aws/cli-agent-orchestrator/logs/terminal/{terminal_id}.log")
PY
}

mkdir -p "$WORKSPACE_DIR"
log "workspace: $WORKSPACE_DIR"
log "using allowlisted env names: ANTHROPIC_API_KEY ANTHROPIC_BASE_URL"
log "target output file: $OUTPUT_FILE_REL"
log "CAO profile store: $CAO_PROFILE_STORE"

trap cleanup EXIT

if ! command -v tmux >/dev/null 2>&1; then
  skip "tmux not found on PATH"
fi

require_local_cao

if [[ ! -f "$AGENT_DEF_DIR/brains/api-creds/claude/personal-a-default/env/vars.env" ]]; then
  skip "missing credential env file for claude profile personal-a-default"
fi

ensure_cao_server

PROMPT_PATH="$WORKSPACE_DIR/prompt.txt"
render_prompt "$SCRIPT_DIR/inputs/prompt_template.txt" "$PROMPT_PATH"
PROMPT="$(<"$PROMPT_PATH")"

run_cmd build pixi run python -m gig_agents.agents.realm_controller build-brain \
  --agent-def-dir "$AGENT_DEF_DIR" \
  --runtime-root "$RUNTIME_ROOT" \
  --tool claude \
  --skill openspec-apply-change \
  --config-profile default \
  --cred-profile personal-a-default

MANIFEST_PATH="$(extract_json_field "$WORKSPACE_DIR/build.log" manifest_path)"

run_cmd start pixi run python -m gig_agents.agents.realm_controller start-session \
  --agent-def-dir "$AGENT_DEF_DIR" \
  --runtime-root "$RUNTIME_ROOT" \
  --brain-manifest "$MANIFEST_PATH" \
  --role gpu-kernel-coder \
  --backend cao_rest \
  --cao-base-url "$CAO_BASE_URL" \
  --cao-profile-store "$CAO_PROFILE_STORE" \
  --workdir "$REPO_ROOT"

SESSION_MANIFEST="$(extract_json_field "$WORKSPACE_DIR/start.log" session_manifest)"

run_cmd prompt pixi run python -m gig_agents.agents.realm_controller send-prompt \
  --agent-def-dir "$AGENT_DEF_DIR" \
  --agent-identity "$SESSION_MANIFEST" \
  --prompt "$PROMPT"

RESPONSE_TEXT="$(extract_response_text "$WORKSPACE_DIR/prompt.log")"
if [[ -z "${RESPONSE_TEXT// }" ]]; then
  fail "prompt response was empty"
fi

verify_generated_file
verify_repo_clean

mapfile -t SESSION_CAO_FIELDS < <(extract_session_cao_fields "$SESSION_MANIFEST")
SESSION_NAME="${SESSION_CAO_FIELDS[0]}"
TERMINAL_ID="${SESSION_CAO_FIELDS[1]}"
TERMINAL_LOG_PATH="${SESSION_CAO_FIELDS[2]}"

if pixi run python -m gig_agents.agents.realm_controller stop-session \
  --agent-def-dir "$AGENT_DEF_DIR" \
  --agent-identity "$SESSION_MANIFEST" >"$WORKSPACE_DIR/stop.log" 2>&1; then
  SESSION_STOPPED=1
fi

pixi run python - "$REPORT_PATH" "$SESSION_MANIFEST" "$WORKSPACE_DIR" "$RESPONSE_TEXT" "$OUTPUT_FILE_REL" "$SENTINEL" "$SENTINEL_OUTPUT" "$GIT_DIFF_OUTPUT" "$SESSION_NAME" "$TERMINAL_ID" "$TERMINAL_LOG_PATH" <<'PY'
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

report_path = Path(sys.argv[1])
session_manifest = sys.argv[2]
workspace = sys.argv[3]
response_text = sys.argv[4]
output_file = sys.argv[5]
sentinel = sys.argv[6]
sentinel_output = sys.argv[7]
git_diff_output = sys.argv[8]
session_name = sys.argv[9]
terminal_id = sys.argv[10]
terminal_log_path = sys.argv[11]

payload = {
    "status": "ok",
    "backend": "cao_rest",
    "tool": "claude",
    "response_text": response_text,
    "session_manifest": session_manifest,
    "workspace": workspace,
    "output_file": output_file,
    "sentinel_expected": sentinel,
    "sentinel_actual": sentinel_output,
    "sentinel_match": sentinel_output == sentinel,
    "git_diff_name_only": [
        line.strip() for line in git_diff_output.splitlines() if line.strip()
    ],
    "session_name": session_name,
    "terminal_id": terminal_id,
    "terminal_log_path": terminal_log_path,
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
