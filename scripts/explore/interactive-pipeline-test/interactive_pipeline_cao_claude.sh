#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Hard-coded brain selection defaults for easy invocation.
DEFAULT_TOOL="claude"
DEFAULT_SKILL="openspec-apply-change"
DEFAULT_CONFIG_PROFILE="default"
DEFAULT_CRED_PROFILE="personal-a-default"
DEFAULT_ROLE="gpu-kernel-coder"

usage() {
  cat <<'EOF'
Launch an interactive CAO-backed Claude agent session (manual follow-up workflow).

Usage:
  interactive_pipeline_cao_claude.sh --agent-identity <name> [options]

Required:
  --agent-identity <name>   Requested CAO agent identity (name form).

Options:
  --agent-def-dir <path>        Agent definition directory (default: auto-detected).
  --runtime-root <path>     Runtime root directory (default: tmp/interactive-pipeline-test/runtime/<timestamp_pid>).
  --workdir <path>          Working directory for launched agent (default: agent-definition root).
  --cao-base-url <url>      CAO base URL (default: $CAO_BASE_URL or http://localhost:9889).
  --skip-cao-healthcheck    Skip CAO /health pre-check.
  -h, --help                Show this message.

Notes:
  - Brain selection is hard-coded for convenience:
      tool=claude
      skill=openspec-apply-change
      config-profile=default
      cred-profile=personal-a-default
      role=gpu-kernel-coder
  - If ANTHROPIC_MODEL is unset, this script sets ANTHROPIC_MODEL=opus.
  - This script does not attach tmux, does not send prompts, and does not stop sessions.
EOF
}

fail() {
  echo "[interactive-pipeline-test][error] $*" >&2
  exit 2
}

log() {
  echo "[interactive-pipeline-test] $*"
}

extract_json_field() {
  local json_path="$1"
  local field_name="$2"
  pixi run python - "$json_path" "$field_name" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
name = sys.argv[2]
if name not in payload:
    raise SystemExit(1)
value = payload[name]
if value is None:
    raise SystemExit(1)
print(value)
PY
}

is_cao_server_healthy() {
  local base_url="$1"
  pixi run python - "$base_url" <<'PY'
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

AGENT_IDENTITY=""
REPO_ROOT=""
AGENT_DEF_DIR="${AGENT_DEF_DIR:-}"
RUNTIME_ROOT=""
WORKDIR=""
CAO_BASE_URL_ARG="${CAO_BASE_URL:-http://localhost:9889}"
SKIP_CAO_HEALTHCHECK=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent-identity)
      shift
      [[ $# -gt 0 ]] || fail "--agent-identity requires a value"
      AGENT_IDENTITY="$1"
      ;;
    --agent-def-dir)
      shift
      [[ $# -gt 0 ]] || fail "--agent-def-dir requires a value"
      AGENT_DEF_DIR="$1"
      ;;
    --runtime-root)
      shift
      [[ $# -gt 0 ]] || fail "--runtime-root requires a value"
      RUNTIME_ROOT="$1"
      ;;
    --workdir)
      shift
      [[ $# -gt 0 ]] || fail "--workdir requires a value"
      WORKDIR="$1"
      ;;
    --cao-base-url)
      shift
      [[ $# -gt 0 ]] || fail "--cao-base-url requires a value"
      CAO_BASE_URL_ARG="$1"
      ;;
    --skip-cao-healthcheck)
      SKIP_CAO_HEALTHCHECK=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "unknown option: $1"
      ;;
  esac
  shift
done

[[ -n "$AGENT_IDENTITY" ]] || fail "missing --agent-identity"

if [[ -z "$REPO_ROOT" ]]; then
  if git -C "$SCRIPT_DIR" rev-parse --show-toplevel >/dev/null 2>&1; then
    REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
  else
    REPO_ROOT="$DEFAULT_REPO_ROOT"
  fi
fi
REPO_ROOT="$(cd "$REPO_ROOT" && pwd)"
if [[ -z "$AGENT_DEF_DIR" ]]; then
  AGENT_DEF_DIR="$REPO_ROOT/tests/fixtures/agents"
fi
AGENT_DEF_DIR="$(cd "$AGENT_DEF_DIR" && pwd)"

if [[ -z "$WORKDIR" ]]; then
  WORKDIR="$REPO_ROOT"
fi
WORKDIR="$(cd "$WORKDIR" && pwd)"

if [[ -z "$RUNTIME_ROOT" ]]; then
  RUN_ID="$(date +%Y%m%d_%H%M%S)_$$"
  RUNTIME_ROOT="$REPO_ROOT/tmp/interactive-pipeline-test/runtime/$RUN_ID"
fi
mkdir -p "$RUNTIME_ROOT"
RUNTIME_ROOT="$(cd "$RUNTIME_ROOT" && pwd)"

CAO_BASE_URL_ARG="${CAO_BASE_URL_ARG%/}"

command -v pixi >/dev/null 2>&1 || fail "pixi not found on PATH"
command -v tmux >/dev/null 2>&1 || fail "tmux not found on PATH"

CRED_ENV_FILE="$AGENT_DEF_DIR/brains/api-creds/claude/$DEFAULT_CRED_PROFILE/env/vars.env"
[[ -f "$CRED_ENV_FILE" ]] || fail "missing credential env file: $CRED_ENV_FILE"

if [[ "$SKIP_CAO_HEALTHCHECK" -eq 0 ]]; then
  if ! is_cao_server_healthy "$CAO_BASE_URL_ARG"; then
    fail "CAO server is not healthy at $CAO_BASE_URL_ARG (use --skip-cao-healthcheck to bypass pre-check)"
  fi
fi

if [[ -z "${ANTHROPIC_MODEL:-}" ]]; then
  export ANTHROPIC_MODEL="opus"
  log "ANTHROPIC_MODEL unset; defaulting to opus for this launch."
else
  log "Using caller-provided ANTHROPIC_MODEL=$ANTHROPIC_MODEL"
fi

BUILD_JSON="$RUNTIME_ROOT/build.json"
START_JSON="$RUNTIME_ROOT/start.json"

log "Building Claude brain (hard-coded defaults) ..."
pixi run python -m gig_agents.agents.brain_launch_runtime build-brain \
  --agent-def-dir "$AGENT_DEF_DIR" \
  --runtime-root "$RUNTIME_ROOT" \
  --tool "$DEFAULT_TOOL" \
  --skill "$DEFAULT_SKILL" \
  --config-profile "$DEFAULT_CONFIG_PROFILE" \
  --cred-profile "$DEFAULT_CRED_PROFILE" \
  >"$BUILD_JSON"

BRAIN_MANIFEST="$(extract_json_field "$BUILD_JSON" manifest_path)" || {
  fail "failed to parse manifest_path from $BUILD_JSON"
}

log "Starting CAO-backed session ..."
pixi run python -m gig_agents.agents.brain_launch_runtime start-session \
  --agent-def-dir "$AGENT_DEF_DIR" \
  --runtime-root "$RUNTIME_ROOT" \
  --brain-manifest "$BRAIN_MANIFEST" \
  --role "$DEFAULT_ROLE" \
  --backend cao_rest \
  --agent-identity "$AGENT_IDENTITY" \
  --cao-base-url "$CAO_BASE_URL_ARG" \
  --workdir "$WORKDIR" \
  >"$START_JSON"

SESSION_MANIFEST="$(extract_json_field "$START_JSON" session_manifest)" || {
  fail "failed to parse session_manifest from $START_JSON"
}
RESOLVED_AGENT_IDENTITY="$(extract_json_field "$START_JSON" agent_identity)" || {
  fail "failed to parse agent_identity from $START_JSON"
}

log "Launch complete."
echo
echo "Session details:"
echo "  agent_identity: $RESOLVED_AGENT_IDENTITY"
echo "  session_manifest: $SESSION_MANIFEST"
echo "  runtime_root: $RUNTIME_ROOT"
echo
echo "Manual next steps (human-gated):"
echo "  1) Attach tmux manually:"
echo "     tmux attach -t $RESOLVED_AGENT_IDENTITY"
echo
echo "  2) Send one prompt turn when ready:"
echo "     $SCRIPT_DIR/send_prompt.sh --agent-identity $RESOLVED_AGENT_IDENTITY \"<your prompt>\""
echo
echo "  3) After each turn, inspect tmux and only then send the next prompt."
echo
echo "  4) Stop session only when explicitly done:"
echo "     pixi run python -m gig_agents.agents.brain_launch_runtime stop-session \\"
echo "       --agent-def-dir $AGENT_DEF_DIR --agent-identity $RESOLVED_AGENT_IDENTITY"
