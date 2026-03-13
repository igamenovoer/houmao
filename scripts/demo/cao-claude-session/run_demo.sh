#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
AGENT_DEF_DIR="${AGENT_DEF_DIR:-$REPO_ROOT/tests/fixtures/agents}"
WORKSPACE_PARENT="${DEMO_WORKSPACE_PARENT:-$HOME/tmp}"
WORKSPACE_SUBDIR="${DEMO_WORKSPACE_SUBDIR:-agent-system-dissect}"
WORKSPACE_ROOT="${WORKSPACE_PARENT%/}/${WORKSPACE_SUBDIR}"
WORKSPACE_DIR="$WORKSPACE_ROOT/demo_cao_claude_$(date +%Y%m%d_%H%M%S)_$$"
RUNTIME_ROOT="$WORKSPACE_DIR/runtime"
REPORT_PATH="$WORKSPACE_DIR/report.json"
CAO_BASE_URL="${CAO_BASE_URL:-http://localhost:9889}"
CAO_BASE_URL="${CAO_BASE_URL%/}"
CAO_LAUNCHER_CONFIG_PATH="$WORKSPACE_DIR/cao-server-launcher.toml"
CAO_LAUNCHER_HOME_DIR="${CAO_LAUNCHER_HOME_DIR:-$WORKSPACE_ROOT}"
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
  echo "[demo][cao-claude] $*"
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

is_cao_server_healthy() {
  pixi run python - "$CAO_BASE_URL" <<'PY'
import json
import sys
import urllib.error
import urllib.request

url = sys.argv[1].rstrip("/") + "/health"
try:
    with urllib.request.urlopen(url, timeout=3) as response:
        payload = json.loads(response.read().decode("utf-8"))
except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
    raise SystemExit(1)

if payload.get("status") != "ok":
    raise SystemExit(1)
if payload.get("service") not in ("cli-agent-orchestrator", None):
    raise SystemExit(1)
raise SystemExit(0)
PY
}

cao_url_is_supported_loopback() {
  [[ "$CAO_BASE_URL" =~ ^http://(localhost|127\.0\.0\.1):[0-9]+$ ]]
}

ensure_cao_server() {
  write_cao_launcher_config

  if ! command -v cao-server >/dev/null 2>&1; then
    fail "cao-server not found on PATH"
  fi

  if ! cao_url_is_supported_loopback && ! is_cao_server_healthy; then
    skip "CAO server is unavailable at ${CAO_BASE_URL} (demo auto-starts only for supported loopback CAO_BASE_URL values like http://localhost:9889 or http://127.0.0.1:9991)"
  fi

  local server_log_path="$WORKSPACE_DIR/cao-server.log"
  local launcher_output_path="$WORKSPACE_DIR/cao-start.json"
  local launcher_error_path="$WORKSPACE_DIR/cao-start.err"
  local launcher_state=""
  local started_new_process="0"
  local reused_existing_process="0"
  local resolved_pid=""
  local killed_count="0"

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

  terminate_local_cao_server_on_base_url() {
    pixi run python - "$CAO_BASE_URL" <<'PY'
from __future__ import annotations

import os
import signal
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

parsed = urlsplit(sys.argv[1].strip().rstrip("/"))
port = parsed.port
if port is None:
    print("0")
    raise SystemExit(0)

def _iter_listener_inodes(table_path: str) -> set[str]:
    path = Path(table_path)
    if not path.exists():
        return set()

    inodes: set[str] = set()
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
        columns = line.split()
        if len(columns) < 10:
            continue
        local_address = columns[1]
        state = columns[3]
        inode = columns[9]
        if state != "0A":  # LISTEN
            continue

        host_hex, port_hex = local_address.split(":")
        if int(port_hex, 16) != port:
            continue

        if table_path.endswith("tcp"):
            if host_hex not in {"0100007F", "00000000"}:  # 127.0.0.1 / 0.0.0.0
                continue
        else:
            if host_hex not in {
                "00000000000000000000000000000001",  # ::1
                "00000000000000000000000000000000",  # ::
            }:
                continue

        inodes.add(inode)
    return inodes

listener_inodes = _iter_listener_inodes("/proc/net/tcp") | _iter_listener_inodes("/proc/net/tcp6")
if not listener_inodes:
    print("0")
    raise SystemExit(0)

pids: set[int] = set()
for proc_entry in Path("/proc").iterdir():
    if not proc_entry.name.isdigit():
        continue
    fd_dir = proc_entry / "fd"
    if not fd_dir.exists():
        continue
    try:
        fd_entries = list(fd_dir.iterdir())
    except OSError:
        continue

    for fd_entry in fd_entries:
        try:
            target = os.readlink(fd_entry)
        except OSError:
            continue
        if not target.startswith("socket:["):
            continue
        inode = target[8:-1]
        if inode in listener_inodes:
            pids.add(int(proc_entry.name))
            break

killed: list[int] = []
for pid in sorted(pids):
    cmdline_path = Path("/proc") / str(pid) / "cmdline"
    try:
        cmdline = cmdline_path.read_bytes().decode("utf-8", errors="replace").replace("\x00", " ")
    except OSError:
        continue
    if "cao-server" not in cmdline:
        continue
    try:
        os.kill(pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        continue
    killed.append(pid)

alive = killed[:]
deadline = time.monotonic() + 5.0
while alive and time.monotonic() < deadline:
    still_alive: list[int] = []
    for pid in alive:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            continue
        except PermissionError:
            still_alive.append(pid)
            continue
        still_alive.append(pid)
    if not still_alive:
        break
    alive = still_alive
    time.sleep(0.1)

for pid in alive:
    try:
        os.kill(pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass

print(str(len(killed)))
PY
  }

  log "starting cao-server via launcher (log: $server_log_path)"
  if ! pixi run python -m gig_agents.cao.tools.cao_server_launcher start \
    --config "$CAO_LAUNCHER_CONFIG_PATH" >"$launcher_output_path" 2>"$launcher_error_path"; then
    fail "cao-server launcher start failed (see $launcher_error_path)"
  fi

  launcher_state="$(parse_launcher_start_state "$launcher_output_path")"
  IFS=":" read -r started_new_process reused_existing_process resolved_pid <<<"$launcher_state"

  if cao_url_is_supported_loopback && [[ "$reused_existing_process" -eq 1 && -z "$resolved_pid" ]]; then
    log "detected an untracked healthy CAO server at ${CAO_BASE_URL}; restarting to align demo runtime context"
    killed_count="$(terminate_local_cao_server_on_base_url || echo "0")"
    log "terminated ${killed_count} existing local cao-server process(es) on ${CAO_BASE_URL}"

    if ! pixi run python -m gig_agents.cao.tools.cao_server_launcher start \
      --config "$CAO_LAUNCHER_CONFIG_PATH" >"$launcher_output_path" 2>"$launcher_error_path"; then
      fail "cao-server launcher restart failed (see $launcher_error_path)"
    fi

    launcher_state="$(parse_launcher_start_state "$launcher_output_path")"
    IFS=":" read -r started_new_process reused_existing_process resolved_pid <<<"$launcher_state"
  fi

  if [[ "$reused_existing_process" -eq 1 && -z "$resolved_pid" ]]; then
    fail "launcher reused an untracked CAO server at ${CAO_BASE_URL}; stop the existing server and retry"
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
log "workspace root override via DEMO_WORKSPACE_PARENT/DEMO_WORKSPACE_SUBDIR"
log "using allowlisted env names: ANTHROPIC_API_KEY ANTHROPIC_BASE_URL"
log "CAO profile store: $CAO_PROFILE_STORE"

trap cleanup EXIT

if ! command -v tmux >/dev/null 2>&1; then
  fail "tmux not found on PATH"
fi

if [[ ! -f "$AGENT_DEF_DIR/brains/api-creds/claude/personal-a-default/env/vars.env" ]]; then
  skip "missing credential env file for claude profile personal-a-default"
fi

ensure_cao_server

cp "$SCRIPT_DIR/inputs/prompt.txt" "$WORKSPACE_DIR/prompt.txt"
PROMPT="$(<"$WORKSPACE_DIR/prompt.txt")"

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
  --workdir "$WORKSPACE_DIR"

SESSION_MANIFEST="$(extract_json_field "$WORKSPACE_DIR/start.log" session_manifest)"

run_cmd prompt pixi run python -m gig_agents.agents.realm_controller send-prompt \
  --agent-def-dir "$AGENT_DEF_DIR" \
  --agent-identity "$SESSION_MANIFEST" \
  --prompt "$PROMPT"

RESPONSE_TEXT="$(extract_response_text "$WORKSPACE_DIR/prompt.log")"
if [[ -z "${RESPONSE_TEXT// }" ]]; then
  fail "prompt response was empty"
fi

if pixi run python -m gig_agents.agents.realm_controller stop-session \
  --agent-def-dir "$AGENT_DEF_DIR" \
  --agent-identity "$SESSION_MANIFEST" >"$WORKSPACE_DIR/stop.log" 2>&1; then
  SESSION_STOPPED=1
fi

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
    "backend": "cao_rest",
    "tool": "claude",
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
