#!/usr/bin/env bash
# Launch Claude Code against the H20-hosted Qwen3.8 Anthropic-compatible API.
#
# The H20 SGLang service (127.0.0.1:14888) exposes an Anthropic Messages route
# at /v1/messages, so ANTHROPIC_BASE_URL points at the server root and Claude
# Code appends /v1/messages itself.
#
# Overrides:
#   QWEN_ANTHROPIC_BASE_URL   server root (default: http://127.0.0.1:14888)
#   QWEN_ANTHROPIC_MODEL      model name (default: Qwen/Qwen3.8-27B-FP8)
#   QWEN_ANTHROPIC_API_KEY    auth token sent as bearer (default: EMPTY)
#   CLAUDE_CONFIG_DIR         Claude Code state dir (default: tmp/.../claude-qwen)
#   CLAUDE_SKIP_PERMISSIONS   set to 0 to keep permission prompts
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/../../../.." && pwd)"

base_url="${QWEN_ANTHROPIC_BASE_URL:-http://127.0.0.1:14888}"
base_url="${base_url%/}"
base_url="${base_url%/v1}"
model="${QWEN_ANTHROPIC_MODEL:-Qwen/Qwen3.8-27B-FP8}"
api_key="${QWEN_ANTHROPIC_API_KEY:-EMPTY}"

if ! command -v claude >/dev/null 2>&1; then
  echo "error: claude is not on PATH" >&2
  exit 1
fi

if command -v curl >/dev/null 2>&1; then
  if ! curl -fsS -m 5 "$base_url/v1/models" >/dev/null; then
    echo "error: no model server at $base_url (start the H20 tunnel/service first)" >&2
    exit 1
  fi
fi

# Keep trial sessions and their native logs out of the user's ~/.claude.
export CLAUDE_CONFIG_DIR="${CLAUDE_CONFIG_DIR:-$repo_root/tmp/expose-agent-usage-records/claude-qwen}"
mkdir -p "$CLAUDE_CONFIG_DIR"

# Route Claude Code at the local endpoint. AUTH_TOKEN avoids the interactive
# API-key approval prompt that ANTHROPIC_API_KEY triggers.
export ANTHROPIC_BASE_URL="$base_url"
export ANTHROPIC_AUTH_TOKEN="$api_key"
unset ANTHROPIC_API_KEY CLAUDE_CODE_OAUTH_TOKEN

# The server serves one model; pin every Claude Code model lane to it.
export ANTHROPIC_MODEL="$model"
export ANTHROPIC_DEFAULT_MODEL="$model"
export ANTHROPIC_DEFAULT_OPUS_MODEL="$model"
export ANTHROPIC_DEFAULT_SONNET_MODEL="$model"
export ANTHROPIC_DEFAULT_HAIKU_MODEL="$model"
export ANTHROPIC_DEFAULT_FABLE_MODEL="$model"
export ANTHROPIC_SMALL_FAST_MODEL="$model"
export CLAUDE_CODE_SUBAGENT_MODEL="$model"

export API_TIMEOUT_MS="${API_TIMEOUT_MS:-300000}"
export CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS="${CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS:-1}"

# The served window is 262144 tokens. Send no effort level so the server's
# own xhigh default applies; Claude Code's explicit levels are rejected.
export CLAUDE_CODE_MAX_CONTEXT_TOKENS="${CLAUDE_CODE_MAX_CONTEXT_TOKENS:-262144}"
export CLAUDE_CODE_EFFORT_LEVEL="${CLAUDE_CODE_EFFORT_LEVEL:-auto}"

echo "claude -> $base_url | model: $model | config: $CLAUDE_CONFIG_DIR" >&2

claude_args=()
if [[ "${CLAUDE_SKIP_PERMISSIONS:-1}" != "0" ]]; then
  claude_args+=(--dangerously-skip-permissions)
fi

exec claude "${claude_args[@]}" "$@"
