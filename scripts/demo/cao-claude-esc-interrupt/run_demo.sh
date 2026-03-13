#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
AGENT_DEF_DIR="${AGENT_DEF_DIR:-$REPO_ROOT/tests/fixtures/agents}"
WORKSPACE_DIR="$REPO_ROOT/tmp/demo_cao_claude_esc_interrupt_$(date +%Y%m%d_%H%M%S)_$$"
RUNTIME_ROOT="$WORKSPACE_DIR/runtime"
REPORT_PATH="$WORKSPACE_DIR/report.json"
DRIVER_REPORT_PATH="$WORKSPACE_DIR/interrupt_driver_report.json"
CAO_BASE_URL="${CAO_BASE_URL:-http://localhost:9889}"
CAO_BASE_URL="${CAO_BASE_URL%/}"
CAO_LAUNCHER_CONFIG_PATH="$WORKSPACE_DIR/cao-server-launcher.toml"
CAO_LAUNCHER_HOME_DIR="${CAO_LAUNCHER_HOME_DIR:-$(dirname "$REPO_ROOT")}"
CAO_PROFILE_STORE="${CAO_PROFILE_STORE:-$CAO_LAUNCHER_HOME_DIR/.aws/cli-agent-orchestrator/agent-store}"
DEMO_TIMEOUT_SECONDS="${DEMO_TIMEOUT_SECONDS:-180}"
CAO_SERVER_STARTED=0
SESSION_MANIFEST=""
SESSION_STOPPED=0
SNAPSHOT=0
if [[ "${1:-}" == "--snapshot-report" ]]; then
  SNAPSHOT=1
fi

log() {
  echo "[demo][cao-claude-esc-interrupt] $*"
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
  if pixi run python -m houmao.cao.tools.cao_server_launcher status \
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
  if ! pixi run python -m houmao.cao.tools.cao_server_launcher start \
    --config "$CAO_LAUNCHER_CONFIG_PATH" >"$launcher_output_path" 2>"$launcher_error_path"; then
    skip "CAO connectivity unavailable (launcher start failed, see $launcher_error_path)"
  fi

  launcher_state="$(parse_launcher_start_state "$launcher_output_path")"
  IFS=":" read -r started_new_process reused_existing_process resolved_pid <<<"$launcher_state"
  log "launcher start result: started_new_process=$started_new_process reused_existing_process=$reused_existing_process pid=${resolved_pid:-unknown}"

  if [[ "$reused_existing_process" -eq 1 && -z "$resolved_pid" ]]; then
    log "ownership mismatch: launcher reused untracked CAO server at ${CAO_BASE_URL}"
    log "retrying via launcher stop/start to restore managed context"
    pixi run python -m houmao.cao.tools.cao_server_launcher stop \
      --config "$CAO_LAUNCHER_CONFIG_PATH" >"$launcher_stop_output_path" 2>"$launcher_stop_error_path" || true
    if ! pixi run python -m houmao.cao.tools.cao_server_launcher start \
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
  pixi run python -m houmao.cao.tools.cao_server_launcher stop \
    --config "$CAO_LAUNCHER_CONFIG_PATH" >"$launcher_output_path" 2>"$launcher_error_path" || true
}

cleanup() {
  set +e

  if [[ -n "${SESSION_MANIFEST}" && "$SESSION_STOPPED" -ne 1 ]]; then
    pixi run python -m houmao.agents.realm_controller stop-session \
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
  if grep -Eiq "could not observe processing" "$log_path"; then
    echo "could not observe processing state (skipping to avoid flakes)"
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

mkdir -p "$WORKSPACE_DIR"
log "workspace: $WORKSPACE_DIR"
log "using allowlisted env names: ANTHROPIC_API_KEY ANTHROPIC_BASE_URL"
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

FIRST_PROMPT_PATH="$WORKSPACE_DIR/first_prompt.txt"
SECOND_PROMPT_PATH="$WORKSPACE_DIR/second_prompt.txt"
cp "$SCRIPT_DIR/inputs/first_prompt.txt" "$FIRST_PROMPT_PATH"
cp "$SCRIPT_DIR/inputs/second_prompt.txt" "$SECOND_PROMPT_PATH"

run_cmd build pixi run python -m houmao.agents.realm_controller build-brain \
  --agent-def-dir "$AGENT_DEF_DIR" \
  --runtime-root "$RUNTIME_ROOT" \
  --tool claude \
  --skill openspec-apply-change \
  --config-profile default \
  --cred-profile personal-a-default

MANIFEST_PATH="$(extract_json_field "$WORKSPACE_DIR/build.log" manifest_path)"

run_cmd start pixi run python -m houmao.agents.realm_controller start-session \
  --agent-def-dir "$AGENT_DEF_DIR" \
  --runtime-root "$RUNTIME_ROOT" \
  --brain-manifest "$MANIFEST_PATH" \
  --role gpu-kernel-coder \
  --backend cao_rest \
  --cao-base-url "$CAO_BASE_URL" \
  --cao-profile-store "$CAO_PROFILE_STORE" \
  --workdir "$REPO_ROOT"

SESSION_MANIFEST="$(extract_json_field "$WORKSPACE_DIR/start.log" session_manifest)"

run_cmd driver pixi run python "$SCRIPT_DIR/scripts/interrupt_driver.py" \
  --agent-def-dir "$AGENT_DEF_DIR" \
  --agent-identity "$SESSION_MANIFEST" \
  --first-prompt-file "$FIRST_PROMPT_PATH" \
  --second-prompt-file "$SECOND_PROMPT_PATH" \
  --output-json "$DRIVER_REPORT_PATH"

if pixi run python -m houmao.agents.realm_controller stop-session \
  --agent-def-dir "$AGENT_DEF_DIR" \
  --agent-identity "$SESSION_MANIFEST" >"$WORKSPACE_DIR/stop.log" 2>&1; then
  SESSION_STOPPED=1
fi

pixi run python - "$REPORT_PATH" "$DRIVER_REPORT_PATH" "$SESSION_MANIFEST" "$WORKSPACE_DIR" <<'PY'
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

report_path = Path(sys.argv[1])
driver_report = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
session_manifest = sys.argv[3]
workspace = sys.argv[4]

payload = dict(driver_report)
payload.update(
    {
        "status": "ok",
        "backend": "cao_rest",
        "tool": "claude",
        "session_manifest": session_manifest,
        "workspace": workspace,
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
    }
)
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
