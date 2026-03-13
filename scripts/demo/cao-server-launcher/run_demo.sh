#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
AGENT_DEF_DIR="${AGENT_DEF_DIR:-$REPO_ROOT/tests/fixtures/agents}"
WORKSPACE_PARENT="${DEMO_WORKSPACE_PARENT:-$HOME/tmp}"
WORKSPACE_SUBDIR="${DEMO_WORKSPACE_SUBDIR:-agent-system-dissect}"
WORKSPACE_ROOT="${WORKSPACE_PARENT%/}/${WORKSPACE_SUBDIR}"
WORKSPACE_DIR="$WORKSPACE_ROOT/demo_cao_server_launcher_$(date +%Y%m%d_%H%M%S)_$$"
RUNTIME_ROOT="$WORKSPACE_DIR/runtime"
CAO_HOME_DIR="$WORKSPACE_DIR/cao-home"
REPORT_PATH="$WORKSPACE_DIR/report.json"
SANITIZED_REPORT_PATH="$WORKSPACE_DIR/report.sanitized.json"
PARAMS_PATH="$WORKSPACE_DIR/demo_parameters.json"
CONFIG_TEMPLATE_PATH="$WORKSPACE_DIR/launcher_config.template.toml"
CONFIG_PATH="$WORKSPACE_DIR/cao-server-launcher.toml"
EXPECTED_REPORT="$SCRIPT_DIR/expected_report/report.json"
VERIFY_SCRIPT="$SCRIPT_DIR/scripts/verify_report.py"
LAUNCHER_MODULE="houmao.cao.tools.cao_server_launcher"
SNAPSHOT=0
START_COMPLETED=0
STOP_COMPLETED=0
STATUS_TIMEOUT_SECONDS="3.0"
POLL_INTERVAL_SECONDS="0.2"
GRACE_PERIOD_SECONDS="10.0"

usage() {
  cat <<'EOF'
Usage:
  scripts/demo/cao-server-launcher/run_demo.sh [--snapshot-report]
EOF
}

log() {
  echo "[demo][cao-server-launcher] $*"
}

skip() {
  log "SKIP: $*"
  exit 0
}

fail() {
  log "FAIL: $*"
  exit 1
}

extract_json_field() {
  local json_path="$1"
  local field_name="$2"
  pixi run python - "$json_path" "$field_name" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
value = payload[sys.argv[2]]
if isinstance(value, (dict, list)):
    print(json.dumps(value, separators=(",", ":")))
else:
    print(value)
PY
}

write_launcher_config_from_template() {
  local template_path="$1"
  local output_path="$2"
  local base_url="$3"
  local runtime_root="$4"
  local home_dir="$5"
  local proxy_policy="$6"
  local startup_timeout_seconds="$7"
  pixi run python - "$template_path" "$output_path" "$base_url" "$runtime_root" "$home_dir" "$proxy_policy" "$startup_timeout_seconds" <<'PY'
import sys
from pathlib import Path

template = Path(sys.argv[1]).read_text(encoding="utf-8")
rendered = (
    template.replace("__BASE_URL__", sys.argv[3])
    .replace("__RUNTIME_ROOT__", sys.argv[4])
    .replace("__HOME_DIR__", sys.argv[5])
    .replace("__PROXY_POLICY__", sys.argv[6])
    .replace("__STARTUP_TIMEOUT_SECONDS__", sys.argv[7])
)
Path(sys.argv[2]).write_text(rendered, encoding="utf-8")
PY
}

run_launcher_command() {
  local label="$1"
  local command_name="$2"
  shift 2
  local output_path="$WORKSPACE_DIR/${label}.json"
  local error_path="$WORKSPACE_DIR/${label}.err"
  local exit_code=0
  if pixi run python -m "$LAUNCHER_MODULE" "$command_name" --config "$CONFIG_PATH" "$@" >"$output_path" 2>"$error_path"; then
    exit_code=0
  else
    exit_code=$?
  fi
  printf '%s\n' "$exit_code" >"$WORKSPACE_DIR/${label}.exit_code"
  log "${label}: exit=${exit_code}, stdout=${output_path}, stderr=${error_path}"
}

read_exit_code() {
  local label="$1"
  cat "$WORKSPACE_DIR/${label}.exit_code"
}

expect_exit_code_in() {
  local label="$1"
  shift
  local actual
  actual="$(read_exit_code "$label")"
  local expected
  for expected in "$@"; do
    if [[ "$actual" == "$expected" ]]; then
      return 0
    fi
  done
  fail "unexpected exit code for ${label}: ${actual} (expected one of: $*)"
}

classify_start_skip_reason() {
  local error_path="$1"
  if grep -Eiq "health check did not become healthy" "$error_path"; then
    echo "cao-server did not become healthy within startup timeout"
    return 0
  fi
  if grep -Eiq "not found on PATH" "$error_path"; then
    echo "cao-server launcher could not find cao-server on PATH"
    return 0
  fi
  if grep -Eiq "process exited early with code 1" "$error_path"; then
    local launcher_log_path
    launcher_log_path="$(pixi run python - "$error_path" <<'PY'
import json
import re
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
error_text = str(payload.get("error", ""))
match = re.search(r"See `([^`]+)`", error_text)
if match:
    print(match.group(1))
PY
)"
    if [[ -n "$launcher_log_path" ]] && [[ -f "$launcher_log_path" ]] && grep -Eiq "address already in use" "$launcher_log_path"; then
      echo "port 9889 is already in use by another local process"
      return 0
    fi
  fi
  return 1
}

expect_start_success_or_skip() {
  local actual
  actual="$(read_exit_code start)"
  if [[ "$actual" == "0" ]]; then
    return 0
  fi

  local reason
  if reason="$(classify_start_skip_reason "$WORKSPACE_DIR/start.err")"; then
    skip "${reason} (see $WORKSPACE_DIR/start.err)"
  fi

  fail "unexpected exit code for start: ${actual} (expected one of: 0)"
}

ensure_loopback_no_proxy() {
  local merged_no_proxy
  merged_no_proxy="$(pixi run python - "${NO_PROXY:-}" "${no_proxy:-}" <<'PY'
import sys

entries = []
seen = set()
for raw in (sys.argv[1], sys.argv[2]):
    for token in raw.split(","):
        value = token.strip()
        if not value:
            continue
        key = value.lower()
        if key in seen:
            continue
        entries.append(value)
        seen.add(key)

for loopback in ("localhost", "127.0.0.1", "::1"):
    key = loopback.lower()
    if key in seen:
        continue
    entries.append(loopback)
    seen.add(key)

print(",".join(entries))
PY
)"
  export NO_PROXY="$merged_no_proxy"
  export no_proxy="$merged_no_proxy"
}

cleanup() {
  set +e
  if [[ "$START_COMPLETED" -eq 1 && "$STOP_COMPLETED" -eq 0 ]]; then
    log "cleanup: attempting stop because start completed but stop did not"
    pixi run python -m "$LAUNCHER_MODULE" stop \
      --config "$CONFIG_PATH" \
      --grace-period-seconds "$GRACE_PERIOD_SECONDS" \
      --poll-interval-seconds "$POLL_INTERVAL_SECONDS" >"$WORKSPACE_DIR/cleanup_stop.json" 2>"$WORKSPACE_DIR/cleanup_stop.err" || true
  fi
}

case "${1:-}" in
  "")
    ;;
  --snapshot-report)
    SNAPSHOT=1
    ;;
  -h | --help)
    usage
    exit 0
    ;;
  *)
    usage
    fail "unknown argument: ${1}"
    ;;
esac

trap cleanup EXIT

if ! command -v pixi >/dev/null 2>&1; then
  skip "pixi not found on PATH"
fi
if ! pixi run python -V >/dev/null 2>&1; then
  skip "pixi environment is unavailable (run 'pixi install' first)"
fi
if ! command -v cao-server >/dev/null 2>&1; then
  skip "cao-server not found on PATH (install with: uv tool install --upgrade git+https://github.com/imsight-forks/cli-agent-orchestrator.git@hz-release)"
fi

if [[ ! -f "$SCRIPT_DIR/inputs/demo_parameters.json" ]]; then
  fail "missing tracked input: inputs/demo_parameters.json"
fi
if [[ ! -f "$SCRIPT_DIR/inputs/launcher_config.template.toml" ]]; then
  fail "missing tracked input: inputs/launcher_config.template.toml"
fi
if [[ ! -f "$VERIFY_SCRIPT" ]]; then
  fail "missing helper script: scripts/verify_report.py"
fi

mkdir -p "$WORKSPACE_DIR"
mkdir -p "$RUNTIME_ROOT"
mkdir -p "$CAO_HOME_DIR"
cp "$SCRIPT_DIR/inputs/demo_parameters.json" "$PARAMS_PATH"
cp "$SCRIPT_DIR/inputs/launcher_config.template.toml" "$CONFIG_TEMPLATE_PATH"

BASE_URL="$(extract_json_field "$PARAMS_PATH" base_url)"
PROXY_POLICY="$(extract_json_field "$PARAMS_PATH" proxy_policy)"
STARTUP_TIMEOUT_SECONDS="$(extract_json_field "$PARAMS_PATH" startup_timeout_seconds)"
STATUS_TIMEOUT_SECONDS="$(extract_json_field "$PARAMS_PATH" status_timeout_seconds)"
POLL_INTERVAL_SECONDS="$(extract_json_field "$PARAMS_PATH" poll_interval_seconds)"
GRACE_PERIOD_SECONDS="$(extract_json_field "$PARAMS_PATH" grace_period_seconds)"

case "$BASE_URL" in
  http://localhost:9889 | http://127.0.0.1:9889)
    ;;
  *)
    fail "unsupported base_url in inputs/demo_parameters.json: $BASE_URL"
    ;;
esac

write_launcher_config_from_template \
  "$CONFIG_TEMPLATE_PATH" \
  "$CONFIG_PATH" \
  "$BASE_URL" \
  "$RUNTIME_ROOT" \
  "$CAO_HOME_DIR" \
  "$PROXY_POLICY" \
  "$STARTUP_TIMEOUT_SECONDS"
ensure_loopback_no_proxy

log "workspace: $WORKSPACE_DIR"
log "runtime root: $RUNTIME_ROOT"
log "config: $CONFIG_PATH"
log "NO_PROXY: $NO_PROXY"
log "snapshot mode: $SNAPSHOT"

run_launcher_command status_before_start status \
  --status-timeout-seconds "$STATUS_TIMEOUT_SECONDS"
expect_exit_code_in status_before_start 0 2

run_launcher_command start start \
  --status-timeout-seconds "$STATUS_TIMEOUT_SECONDS" \
  --poll-interval-seconds "$POLL_INTERVAL_SECONDS"
expect_start_success_or_skip
START_COMPLETED=1

run_launcher_command status_after_start status \
  --status-timeout-seconds "$STATUS_TIMEOUT_SECONDS"
expect_exit_code_in status_after_start 0

run_launcher_command stop stop \
  --grace-period-seconds "$GRACE_PERIOD_SECONDS" \
  --poll-interval-seconds "$POLL_INTERVAL_SECONDS"
expect_exit_code_in stop 0
STOP_COMPLETED=1

run_launcher_command status_after_stop status \
  --status-timeout-seconds "$STATUS_TIMEOUT_SECONDS"
expect_exit_code_in status_after_stop 0 2

pixi run python - "$REPORT_PATH" "$WORKSPACE_DIR" "$RUNTIME_ROOT" "$PARAMS_PATH" <<'PY'
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit


def load_json(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise RuntimeError(f"missing JSON payload: {path}")
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected object payload at {path}")
    return payload


def read_step(workspace: Path, label: str) -> dict[str, object]:
    stdout_path = workspace / f"{label}.json"
    stderr_path = workspace / f"{label}.err"
    exit_code_path = workspace / f"{label}.exit_code"
    exit_code = int(exit_code_path.read_text(encoding="utf-8").strip())
    payload = load_json(stdout_path)
    return {
        "exit_code": exit_code,
        "payload": payload,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
    }


report_path = Path(sys.argv[1])
workspace = Path(sys.argv[2])
runtime_root = Path(sys.argv[3])
params = load_json(Path(sys.argv[4]))

flow = {
    "status_before_start": read_step(workspace, "status_before_start"),
    "start": read_step(workspace, "start"),
    "status_after_start": read_step(workspace, "status_after_start"),
    "stop": read_step(workspace, "stop"),
    "status_after_stop": read_step(workspace, "status_after_stop"),
}

base_url = str(params["base_url"])
parsed = urlsplit(base_url)
if parsed.hostname is None or parsed.port is None:
    raise RuntimeError(f"invalid base_url for artifact check: {base_url}")
expected_artifact_dir = runtime_root / "cao-server" / f"{parsed.hostname}-{parsed.port}"

start_payload = flow["start"]["payload"]
if not isinstance(start_payload, dict):
    raise RuntimeError("start payload must be an object")
artifact_dir = Path(str(start_payload.get("artifact_dir", "")))
pid_file = Path(str(start_payload.get("pid_file", "")))
log_file = Path(str(start_payload.get("log_file", "")))
launcher_result_file = Path(str(start_payload.get("launcher_result_file", "")))
ownership_file = Path(str(start_payload.get("ownership_file", "")))
ownership_payload = (
    load_json(ownership_file)
    if ownership_file.exists()
    else {}
)
started_new_process = bool(start_payload.get("started_new_process"))
reused_existing_process = bool(start_payload.get("reused_existing_process"))

artifact_checks = {
    "expected_artifact_dir": str(expected_artifact_dir),
    "paths_match": (
        artifact_dir == expected_artifact_dir
        and pid_file == expected_artifact_dir / "cao-server.pid"
        and log_file == expected_artifact_dir / "cao-server.log"
        and launcher_result_file == expected_artifact_dir / "launcher_result.json"
        and ownership_file == expected_artifact_dir / "ownership.json"
    ),
    "artifact_dir_exists_after_start": artifact_dir.exists(),
    "pid_file_exists_after_start": pid_file.exists(),
    "log_file_exists_after_start": log_file.exists(),
    "launcher_result_exists_after_start": launcher_result_file.exists(),
    "ownership_file_exists_after_start": ownership_file.exists(),
    "ownership_metadata_matches": (
        isinstance(ownership_payload, dict)
        and ownership_payload.get("managed_by") == "houmao.cao.server_launcher"
        and ownership_payload.get("launch_mode") == "detached"
        and ownership_payload.get("base_url") == base_url
        and ownership_payload.get("runtime_root") == str(runtime_root)
        and ownership_payload.get("artifact_dir") == str(expected_artifact_dir)
        and ownership_payload.get("pid") == start_payload.get("pid")
    ),
    "ownership_contract_valid": (
        (
            started_new_process
            and ownership_file.exists()
            and isinstance(ownership_payload, dict)
            and ownership_payload.get("managed_by") == "houmao.cao.server_launcher"
            and ownership_payload.get("launch_mode") == "detached"
        )
        or (
            reused_existing_process
            and not ownership_file.exists()
            and start_payload.get("ownership") is None
        )
    ),
}

report = {
    "status": "ok",
    "demo": "cao-server-launcher",
    "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
    "workspace": str(workspace),
    "runtime_root": str(runtime_root),
    "params": params,
    "flow_order": [
        "status_before_start",
        "start",
        "status_after_start",
        "stop",
        "status_after_stop",
    ],
    "flow": flow,
    "artifact_checks": artifact_checks,
}

report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY

if [[ "$SNAPSHOT" -eq 1 ]]; then
  pixi run python "$VERIFY_SCRIPT" \
    "$REPORT_PATH" \
    "$EXPECTED_REPORT" \
    --snapshot \
    --sanitized-output "$SANITIZED_REPORT_PATH"
else
  pixi run python "$VERIFY_SCRIPT" \
    "$REPORT_PATH" \
    "$EXPECTED_REPORT" \
    --sanitized-output "$SANITIZED_REPORT_PATH"
fi

log "demo complete"
log "report: $REPORT_PATH"
log "sanitized report: $SANITIZED_REPORT_PATH"
log "expected report: $EXPECTED_REPORT"
