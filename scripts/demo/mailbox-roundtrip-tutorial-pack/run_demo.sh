#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
HELPER_SCRIPT="$SCRIPT_DIR/scripts/tutorial_pack_helpers.py"
SANITIZE_SCRIPT="$SCRIPT_DIR/scripts/sanitize_report.py"
VERIFY_SCRIPT="$SCRIPT_DIR/scripts/verify_report.py"
EXPECTED_REPORT="$SCRIPT_DIR/expected_report/report.json"
DEMO_TIMEOUT_SECONDS="${DEMO_TIMEOUT_SECONDS:-180}"
SNAPSHOT=0
RAW_DEMO_OUTPUT_DIR=""
RAW_JOBS_DIR=""
print_help() {
  cat <<'EOF'
Usage:
  scripts/demo/mailbox-roundtrip-tutorial-pack/run_demo.sh [--snapshot-report] [--demo-output-dir <path>] [--jobs-dir <path>]
EOF
}
while [[ $# -gt 0 ]]; do
  case "$1" in
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
      echo "unknown argument: ${1}" >&2
      exit 1
      ;;
  esac
done

AGENT_DEF_DIR="${AGENT_DEF_DIR:-}"
BACKEND=""
CAO_BASE_URL="${CAO_BASE_URL:-}"
MAILBOX_ROOT=""
DEMO_OUTPUT_DIR=""
PROJECT_WORKDIR=""
RUNTIME_ROOT=""
INPUTS_DIR=""
REPORT_PATH=""
SANITIZED_REPORT_PATH=""
PARAMS_PATH=""
JOBS_DIR=""
DEMO_EXTERNAL_CAO="${DEMO_EXTERNAL_CAO:-0}"
SENDER_BLUEPRINT=""
SENDER_REQUESTED_IDENTITY=""
SENDER_CONTROL_IDENTITY=""
SENDER_MAILBOX_PRINCIPAL_ID=""
SENDER_MAILBOX_ADDRESS=""
RECEIVER_BLUEPRINT=""
RECEIVER_REQUESTED_IDENTITY=""
RECEIVER_CONTROL_IDENTITY=""
RECEIVER_MAILBOX_PRINCIPAL_ID=""
RECEIVER_MAILBOX_ADDRESS=""
MESSAGE_SUBJECT=""
INITIAL_BODY_FILE=""
REPLY_BODY_FILE=""
CAO_PROFILE_STORE="${CAO_PROFILE_STORE:-}"
CAO_MANAGED=0
CAO_STARTED_BY_RUN=0
CAO_STOPPED=0
SENDER_STOPPED=0
RECEIVER_STOPPED=0
SENDER_STARTED=0
RECEIVER_STARTED=0

log() {
  echo "[demo][mailbox-roundtrip] $*"
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
  local error_path="$1"
  if grep -Eiq "Missing credential profile|Missing credential env file|Missing file" "$error_path"; then
    echo "missing credentials"
    return 0
  fi
  if grep -Eiq "Agent profile not found|Failed to load agent profile" "$error_path"; then
    echo "CAO profile store mismatch"
    return 0
  fi
  if grep -Eiq "401|403|unauthori[sz]ed|forbidden|invalid api key|authentication" "$error_path"; then
    echo "invalid credentials"
    return 0
  fi
  if grep -Eiq "Connection refused|timed out|timeout|network is unreachable|Temporary failure|Name or service not known" "$error_path"; then
    echo "connectivity unavailable"
    return 0
  fi
  return 1
}

json_value() {
  pixi run python "$HELPER_SCRIPT" json-value "$1" "$2"
}

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

run_demo_command() {
  local label="$1"
  shift
  local stdout_path="$DEMO_OUTPUT_DIR/${label}.json"
  local stderr_path="$DEMO_OUTPUT_DIR/${label}.err"
  local exit_code=0
  if command -v timeout >/dev/null 2>&1; then
    if timeout "$DEMO_TIMEOUT_SECONDS" "$@" >"$stdout_path" 2>"$stderr_path"; then
      log "${label}: ok"
      return 0
    fi
    exit_code=$?
  else
    if "$@" >"$stdout_path" 2>"$stderr_path"; then
      log "${label}: ok"
      return 0
    fi
    exit_code=$?
  fi
  if [[ "$exit_code" -eq 124 || "$exit_code" -eq 137 || "$exit_code" -eq 143 ]]; then
    skip "command timed out after ${DEMO_TIMEOUT_SECONDS}s during ${label} (see $stderr_path)"
  fi
  local reason=""
  if reason="$(classify_skip_reason "$stderr_path")"; then
    skip "${reason} (see $stderr_path)"
  fi
  fail "command failed during ${label} (exit=${exit_code}, see $stderr_path)"
}

cleanup() {
  set +e
  if [[ "$RECEIVER_STARTED" -eq 1 && -n "$RECEIVER_CONTROL_IDENTITY" && "$RECEIVER_STOPPED" -ne 1 ]]; then
    log "cleanup: stopping receiver session"
    pixi run python -m houmao.agents.realm_controller stop-session \
      --agent-def-dir "$AGENT_DEF_DIR" \
      --agent-identity "$RECEIVER_CONTROL_IDENTITY" >"$DEMO_OUTPUT_DIR/cleanup_receiver_stop.json" \
      2>"$DEMO_OUTPUT_DIR/cleanup_receiver_stop.err" || true
  fi
  if [[ "$SENDER_STARTED" -eq 1 && -n "$SENDER_CONTROL_IDENTITY" && "$SENDER_STOPPED" -ne 1 ]]; then
    log "cleanup: stopping sender session"
    pixi run python -m houmao.agents.realm_controller stop-session \
      --agent-def-dir "$AGENT_DEF_DIR" \
      --agent-identity "$SENDER_CONTROL_IDENTITY" >"$DEMO_OUTPUT_DIR/cleanup_sender_stop.json" \
      2>"$DEMO_OUTPUT_DIR/cleanup_sender_stop.err" || true
  fi
  if [[ "$CAO_MANAGED" -eq 1 && "$CAO_STARTED_BY_RUN" -eq 1 && "$CAO_STOPPED" -ne 1 ]]; then
    log "cleanup: stopping launcher-managed CAO"
    pixi run python "$HELPER_SCRIPT" stop-demo-cao \
      --repo-root "$REPO_ROOT" \
      --demo-output-dir "$DEMO_OUTPUT_DIR" \
      --cao-base-url "$CAO_BASE_URL" >"$DEMO_OUTPUT_DIR/cleanup_cao_stop.json" \
      2>"$DEMO_OUTPUT_DIR/cleanup_cao_stop.err" || true
    CAO_STOPPED=1
  fi
}

trap cleanup EXIT

if ! command -v pixi >/dev/null 2>&1; then
  skip "pixi not found on PATH"
fi
if ! pixi run python -V >/dev/null 2>&1; then
  skip "pixi environment is unavailable (run 'pixi install' first)"
fi
if ! command -v tmux >/dev/null 2>&1; then
  skip "tmux not found on PATH"
fi
if [[ ! -f "$SCRIPT_DIR/inputs/demo_parameters.json" ]]; then
  fail "missing tracked input: inputs/demo_parameters.json"
fi
if [[ ! -f "$SCRIPT_DIR/inputs/initial_message.md" ]]; then
  fail "missing tracked input: inputs/initial_message.md"
fi
if [[ ! -f "$SCRIPT_DIR/inputs/reply_message.md" ]]; then
  fail "missing tracked input: inputs/reply_message.md"
fi
if [[ ! -f "$HELPER_SCRIPT" || ! -f "$SANITIZE_SCRIPT" || ! -f "$VERIFY_SCRIPT" ]]; then
  fail "missing tutorial helper scripts"
fi

DEMO_OUTPUT_DIR="$(resolve_path "$RAW_DEMO_OUTPUT_DIR" "tmp/demo/mailbox-roundtrip-tutorial-pack")"
PROJECT_WORKDIR="$DEMO_OUTPUT_DIR/project"
RUNTIME_ROOT="$DEMO_OUTPUT_DIR/runtime"
INPUTS_DIR="$DEMO_OUTPUT_DIR/inputs"
REPORT_PATH="$DEMO_OUTPUT_DIR/report.json"
SANITIZED_REPORT_PATH="$DEMO_OUTPUT_DIR/report.sanitized.json"
PARAMS_PATH="$INPUTS_DIR/demo_parameters.json"
if [[ -n "$RAW_JOBS_DIR" ]]; then
  JOBS_DIR="$(resolve_path "$RAW_JOBS_DIR")"
  export AGENTSYS_LOCAL_JOBS_DIR="$JOBS_DIR"
else
  JOBS_DIR=""
fi

mkdir -p "$DEMO_OUTPUT_DIR"
pixi run python "$HELPER_SCRIPT" ensure-project-worktree \
  --repo-root "$REPO_ROOT" \
  --project-workdir "$PROJECT_WORKDIR" >/dev/null
mkdir -p "$RUNTIME_ROOT"
rm -rf "$INPUTS_DIR"
rm -rf "$DEMO_OUTPUT_DIR/shared-mailbox"
rm -f \
  "$DEMO_OUTPUT_DIR"/cao_*.json \
  "$DEMO_OUTPUT_DIR"/cao_*.err \
  "$REPORT_PATH" \
  "$SANITIZED_REPORT_PATH" \
  "$DEMO_OUTPUT_DIR"/sender_*.json \
  "$DEMO_OUTPUT_DIR"/sender_*.err \
  "$DEMO_OUTPUT_DIR"/receiver_*.json \
  "$DEMO_OUTPUT_DIR"/receiver_*.err \
  "$DEMO_OUTPUT_DIR"/mail_*.json \
  "$DEMO_OUTPUT_DIR"/mail_*.err \
  "$DEMO_OUTPUT_DIR"/cleanup_*.json \
  "$DEMO_OUTPUT_DIR"/cleanup_*.err
mkdir -p "$INPUTS_DIR"
cp -R "$SCRIPT_DIR/inputs/." "$INPUTS_DIR/"
pixi run python "$HELPER_SCRIPT" validate-parameters "$PARAMS_PATH" >/dev/null

DEFAULT_AGENT_DEF_DIR="$(json_value "$PARAMS_PATH" agent_def_dir)"
AGENT_DEF_DIR="${AGENT_DEF_DIR:-$REPO_ROOT/$DEFAULT_AGENT_DEF_DIR}"
BACKEND="$(json_value "$PARAMS_PATH" backend)"
CAO_BASE_URL="${CAO_BASE_URL:-$(json_value "$PARAMS_PATH" cao_base_url)}"
CAO_BASE_URL="${CAO_BASE_URL%/}"
MAILBOX_ROOT="$(pixi run python "$HELPER_SCRIPT" render-mailbox-root "$PARAMS_PATH" "$DEMO_OUTPUT_DIR")"

if [[ "$DEMO_EXTERNAL_CAO" == "1" ]]; then
  log "CAO mode: external (DEMO_EXTERNAL_CAO=1)"
elif pixi run python "$HELPER_SCRIPT" supports-loopback-cao --cao-base-url "$CAO_BASE_URL" >/dev/null 2>&1; then
  run_demo_command cao_start \
    pixi run python "$HELPER_SCRIPT" start-demo-cao \
      --repo-root "$REPO_ROOT" \
      --demo-output-dir "$DEMO_OUTPUT_DIR" \
      --cao-base-url "$CAO_BASE_URL"
  CAO_MANAGED=1
  MANAGED_CAO_PROFILE_STORE="$(json_value "$DEMO_OUTPUT_DIR/cao_start.json" profile_store)"
  STARTED_CURRENT_RUN="$(json_value "$DEMO_OUTPUT_DIR/cao_start.json" started_current_run)"
  if [[ "$STARTED_CURRENT_RUN" == "True" || "$STARTED_CURRENT_RUN" == "true" ]]; then
    CAO_STARTED_BY_RUN=1
  fi
  if [[ -n "$CAO_PROFILE_STORE" && "$CAO_PROFILE_STORE" != "$MANAGED_CAO_PROFILE_STORE" ]]; then
    fail "CAO_PROFILE_STORE override does not match the demo-managed CAO profile store"
  fi
  CAO_PROFILE_STORE="$MANAGED_CAO_PROFILE_STORE"
  log "CAO mode: launcher-managed loopback"
else
  log "CAO mode: external (unsupported loopback launcher management for $CAO_BASE_URL)"
fi

if [[ "$CAO_MANAGED" -ne 1 && -z "$CAO_PROFILE_STORE" ]]; then
  skip "external CAO requires explicit CAO_PROFILE_STORE=/abs/path/.../agent-store"
fi
if [[ "$CAO_MANAGED" -ne 1 ]]; then
  skip "external CAO is not part of the default verified tutorial contract; use the manual realm_controller walkthrough with explicit CAO_PROFILE_STORE"
fi

SENDER_BLUEPRINT="$(json_value "$PARAMS_PATH" sender.blueprint)"
SENDER_REQUESTED_IDENTITY="$(json_value "$PARAMS_PATH" sender.agent_identity)"
SENDER_CONTROL_IDENTITY="$SENDER_REQUESTED_IDENTITY"
SENDER_MAILBOX_PRINCIPAL_ID="$(json_value "$PARAMS_PATH" sender.mailbox_principal_id)"
SENDER_MAILBOX_ADDRESS="$(json_value "$PARAMS_PATH" sender.mailbox_address)"

RECEIVER_BLUEPRINT="$(json_value "$PARAMS_PATH" receiver.blueprint)"
RECEIVER_REQUESTED_IDENTITY="$(json_value "$PARAMS_PATH" receiver.agent_identity)"
RECEIVER_CONTROL_IDENTITY="$RECEIVER_REQUESTED_IDENTITY"
RECEIVER_MAILBOX_PRINCIPAL_ID="$(json_value "$PARAMS_PATH" receiver.mailbox_principal_id)"
RECEIVER_MAILBOX_ADDRESS="$(json_value "$PARAMS_PATH" receiver.mailbox_address)"

MESSAGE_SUBJECT="$(json_value "$PARAMS_PATH" message.subject)"
INITIAL_BODY_FILE="$DEMO_OUTPUT_DIR/$(json_value "$PARAMS_PATH" message.initial_body_file)"
REPLY_BODY_FILE="$DEMO_OUTPUT_DIR/$(json_value "$PARAMS_PATH" message.reply_body_file)"

if [[ ! -d "$AGENT_DEF_DIR" ]]; then
  fail "agent definition directory not found: $AGENT_DEF_DIR"
fi
if [[ ! -f "$INITIAL_BODY_FILE" || ! -f "$REPLY_BODY_FILE" ]]; then
  fail "copied message body inputs are missing from the workspace"
fi

log "demo output dir: $DEMO_OUTPUT_DIR"
log "project workdir: $PROJECT_WORKDIR"
log "runtime root: $RUNTIME_ROOT"
log "mailbox root: $MAILBOX_ROOT"
log "agent definitions: $AGENT_DEF_DIR"
if [[ -n "$CAO_PROFILE_STORE" ]]; then
  log "CAO profile store: $CAO_PROFILE_STORE"
fi
if [[ -n "$JOBS_DIR" ]]; then
  log "jobs root override: $JOBS_DIR"
else
  log "jobs root: default under $PROJECT_WORKDIR/.houmao/jobs"
fi

run_demo_command sender_build \
  pixi run python -m houmao.agents.realm_controller build-brain \
    --agent-def-dir "$AGENT_DEF_DIR" \
    --runtime-root "$RUNTIME_ROOT" \
    --blueprint "$SENDER_BLUEPRINT"
SENDER_BRAIN_MANIFEST="$(json_value "$DEMO_OUTPUT_DIR/sender_build.json" manifest_path)"

run_demo_command receiver_build \
  pixi run python -m houmao.agents.realm_controller build-brain \
    --agent-def-dir "$AGENT_DEF_DIR" \
    --runtime-root "$RUNTIME_ROOT" \
    --blueprint "$RECEIVER_BLUEPRINT"
RECEIVER_BRAIN_MANIFEST="$(json_value "$DEMO_OUTPUT_DIR/receiver_build.json" manifest_path)"

SENDER_START_ARGS=(
  pixi run python -m houmao.agents.realm_controller start-session
  --agent-def-dir "$AGENT_DEF_DIR"
  --runtime-root "$RUNTIME_ROOT"
  --brain-manifest "$SENDER_BRAIN_MANIFEST"
  --blueprint "$SENDER_BLUEPRINT"
  --backend "$BACKEND"
  --cao-base-url "$CAO_BASE_URL"
  --workdir "$PROJECT_WORKDIR"
  --agent-identity "$SENDER_REQUESTED_IDENTITY"
  --mailbox-transport filesystem
  --mailbox-root "$MAILBOX_ROOT"
  --mailbox-principal-id "$SENDER_MAILBOX_PRINCIPAL_ID"
  --mailbox-address "$SENDER_MAILBOX_ADDRESS"
)
if [[ -n "$CAO_PROFILE_STORE" ]]; then
  SENDER_START_ARGS+=(--cao-profile-store "$CAO_PROFILE_STORE")
fi
run_demo_command sender_start "${SENDER_START_ARGS[@]}"
SENDER_STARTED=1
SENDER_CONTROL_IDENTITY="$(json_value "$DEMO_OUTPUT_DIR/sender_start.json" agent_identity)"

RECEIVER_START_ARGS=(
  pixi run python -m houmao.agents.realm_controller start-session
  --agent-def-dir "$AGENT_DEF_DIR"
  --runtime-root "$RUNTIME_ROOT"
  --brain-manifest "$RECEIVER_BRAIN_MANIFEST"
  --blueprint "$RECEIVER_BLUEPRINT"
  --backend "$BACKEND"
  --cao-base-url "$CAO_BASE_URL"
  --workdir "$PROJECT_WORKDIR"
  --agent-identity "$RECEIVER_REQUESTED_IDENTITY"
  --mailbox-transport filesystem
  --mailbox-root "$MAILBOX_ROOT"
  --mailbox-principal-id "$RECEIVER_MAILBOX_PRINCIPAL_ID"
  --mailbox-address "$RECEIVER_MAILBOX_ADDRESS"
)
if [[ -n "$CAO_PROFILE_STORE" ]]; then
  RECEIVER_START_ARGS+=(--cao-profile-store "$CAO_PROFILE_STORE")
fi
run_demo_command receiver_start "${RECEIVER_START_ARGS[@]}"
RECEIVER_STARTED=1
RECEIVER_CONTROL_IDENTITY="$(json_value "$DEMO_OUTPUT_DIR/receiver_start.json" agent_identity)"

run_demo_command mail_send \
  pixi run python -m houmao.agents.realm_controller mail send \
    --agent-def-dir "$AGENT_DEF_DIR" \
    --agent-identity "$SENDER_CONTROL_IDENTITY" \
    --to "$RECEIVER_MAILBOX_ADDRESS" \
    --subject "$MESSAGE_SUBJECT" \
    --body-file "$INITIAL_BODY_FILE"
SEND_MESSAGE_ID="$(pixi run python "$HELPER_SCRIPT" message-id "$DEMO_OUTPUT_DIR/mail_send.json")"

run_demo_command receiver_check \
  pixi run python -m houmao.agents.realm_controller mail check \
    --agent-def-dir "$AGENT_DEF_DIR" \
    --agent-identity "$RECEIVER_CONTROL_IDENTITY" \
    --unread-only \
    --limit 10

run_demo_command mail_reply \
  pixi run python -m houmao.agents.realm_controller mail reply \
    --agent-def-dir "$AGENT_DEF_DIR" \
    --agent-identity "$RECEIVER_CONTROL_IDENTITY" \
    --message-id "$SEND_MESSAGE_ID" \
    --body-file "$REPLY_BODY_FILE"

run_demo_command sender_check \
  pixi run python -m houmao.agents.realm_controller mail check \
    --agent-def-dir "$AGENT_DEF_DIR" \
    --agent-identity "$SENDER_CONTROL_IDENTITY" \
    --unread-only \
    --limit 10

run_demo_command sender_stop \
  pixi run python -m houmao.agents.realm_controller stop-session \
    --agent-def-dir "$AGENT_DEF_DIR" \
    --agent-identity "$SENDER_CONTROL_IDENTITY"
SENDER_STOPPED=1

run_demo_command receiver_stop \
  pixi run python -m houmao.agents.realm_controller stop-session \
    --agent-def-dir "$AGENT_DEF_DIR" \
    --agent-identity "$RECEIVER_CONTROL_IDENTITY"
RECEIVER_STOPPED=1

pixi run python "$HELPER_SCRIPT" build-report \
  --output "$REPORT_PATH" \
  --parameters "$PARAMS_PATH" \
  --demo-output-dir "$DEMO_OUTPUT_DIR" \
  --project-workdir "$PROJECT_WORKDIR" \
  --runtime-root "$RUNTIME_ROOT" \
  --mailbox-root "$MAILBOX_ROOT" \
  --agent-def-dir "$AGENT_DEF_DIR" \
  --reply-parent-message-id "$SEND_MESSAGE_ID" >/dev/null
pixi run python "$SANITIZE_SCRIPT" "$REPORT_PATH" "$SANITIZED_REPORT_PATH" >/dev/null

if [[ "$SNAPSHOT" -eq 1 ]]; then
  pixi run python "$VERIFY_SCRIPT" --snapshot "$SANITIZED_REPORT_PATH" "$EXPECTED_REPORT"
else
  pixi run python "$VERIFY_SCRIPT" "$SANITIZED_REPORT_PATH" "$EXPECTED_REPORT"
fi

log "demo complete"
log "report: $REPORT_PATH"
log "sanitized report: $SANITIZED_REPORT_PATH"
