#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

usage() {
  cat <<'EOF'
Send one prompt turn to an interactive CAO-backed session.

Usage:
  send_prompt.sh --agent-identity <identity-or-manifest> --prompt "<text>"
  send_prompt.sh --agent-identity <identity-or-manifest> "<text>"
  AGENT_IDENTITY=<identity-or-manifest> send_prompt.sh "<text>"

Options:
  --agent-identity <value>  Agent identity or session manifest path.
                            Defaults from $AGENT_IDENTITY if set.
  --prompt <text>           Prompt text. If omitted, remaining args are joined.
  --agent-def-dir <path>        Agent definition directory (default: auto-detected).
  -h, --help                Show this message.

Notes:
  - This helper sends exactly one prompt turn and exits.
  - Inspect tmux output manually before sending the next turn.
EOF
}

AGENT_IDENTITY="${AGENT_IDENTITY:-}"
PROMPT=""
REPO_ROOT=""
AGENT_DEF_DIR="${AGENT_DEF_DIR:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --agent-identity)
      shift
      [[ $# -gt 0 ]] || { echo "error: --agent-identity requires a value" >&2; exit 2; }
      AGENT_IDENTITY="$1"
      ;;
    --prompt)
      shift
      [[ $# -gt 0 ]] || { echo "error: --prompt requires a value" >&2; exit 2; }
      PROMPT="$1"
      ;;
    --agent-def-dir)
      shift
      [[ $# -gt 0 ]] || { echo "error: --agent-def-dir requires a value" >&2; exit 2; }
      AGENT_DEF_DIR="$1"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "error: unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      break
      ;;
  esac
  shift
done

if [[ $# -gt 0 ]]; then
  if [[ -n "$PROMPT" ]]; then
    echo "error: prompt provided both by --prompt and positional args" >&2
    exit 2
  fi
  PROMPT="$*"
fi

if [[ -z "$PROMPT" && ! -t 0 ]]; then
  PROMPT="$(cat)"
fi

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

if [[ -z "$AGENT_IDENTITY" ]]; then
  echo "error: missing agent identity. Pass --agent-identity or set AGENT_IDENTITY." >&2
  exit 2
fi

if [[ -z "${PROMPT//[$' \t\r\n']/}" ]]; then
  echo "error: prompt must not be blank" >&2
  exit 2
fi

if ! command -v pixi >/dev/null 2>&1; then
  echo "error: pixi not found on PATH" >&2
  exit 2
fi

pixi run python -m houmao.agents.realm_controller send-prompt \
  --agent-def-dir "$AGENT_DEF_DIR" \
  --agent-identity "$AGENT_IDENTITY" \
  --prompt "$PROMPT"

echo "[interactive-pipeline-test] Prompt sent. Inspect tmux output before next turn."
