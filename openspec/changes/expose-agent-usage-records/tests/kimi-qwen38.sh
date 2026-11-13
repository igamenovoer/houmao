#!/usr/bin/env bash
# Launch Kimi Code against the H20-hosted Qwen3.8 OpenAI-compatible endpoint.
#
# The KIMI_MODEL_* variables synthesize a temporary provider in memory, so
# nothing is written to config.toml. Sessions use an isolated KIMI_CODE_HOME.
#
# Overrides:
#   KIMI_QWEN_HOME        isolated data root (default: tmp/.../kimi-qwen)
#   KIMI_QWEN_BASE_URL    OpenAI-compatible base URL (default: http://127.0.0.1:14888/v1)
#   KIMI_QWEN_MODEL       model id (default: Qwen/Qwen3.8-27B-FP8)
#   KIMI_QWEN_API_KEY     provider key (default: EMPTY)
#   KIMI_SKIP_PERMISSIONS set to 0 to keep approvals (default: --auto)
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/../../../.." && pwd)"

base_url="${KIMI_QWEN_BASE_URL:-http://127.0.0.1:14888/v1}"
model="${KIMI_QWEN_MODEL:-Qwen/Qwen3.8-27B-FP8}"
api_key="${KIMI_QWEN_API_KEY:-EMPTY}"

if ! command -v kimi >/dev/null 2>&1; then
  echo "error: kimi is not on PATH" >&2
  exit 1
fi

if command -v curl >/dev/null 2>&1; then
  if ! curl -fsS -m 5 "${base_url%/}/models" >/dev/null; then
    echo "error: no model server at $base_url (start the H20 tunnel/service first)" >&2
    exit 1
  fi
fi

# Keep sessions and trust state out of the user's ~/.kimi-code.
export KIMI_CODE_HOME="${KIMI_QWEN_HOME:-$repo_root/tmp/expose-agent-usage-records/kimi-qwen}"
mkdir -p "$KIMI_CODE_HOME"
export KIMI_CODE_TRUST_WORKSPACE=1

# Synthesize a temporary Qwen provider for this process only.
export KIMI_MODEL_NAME="$model"
export KIMI_MODEL_API_KEY="$api_key"
export KIMI_MODEL_PROVIDER_TYPE=openai
export KIMI_MODEL_BASE_URL="$base_url"
export KIMI_MODEL_MAX_CONTEXT_SIZE=262144
export KIMI_MODEL_REASONING_KEY=reasoning_content
export KIMI_MODEL_CAPABILITIES="thinking,image_in,tool_use"
export KIMI_MODEL_DISPLAY_NAME="Qwen3.8 27B FP8 (H20)"

# --auto is Kimi's Never Ask mode. It cannot be combined with -p/--prompt,
# which is already non-interactive.
kimi_args=()
if [[ "${KIMI_SKIP_PERMISSIONS:-1}" != "0" ]]; then
  prompt_mode=0
  for arg in "$@"; do
    case "$arg" in
      -p|--prompt|--prompt=*)
        prompt_mode=1
        break
        ;;
    esac
  done
  if (( prompt_mode == 0 )); then
    kimi_args+=(--auto)
  fi
fi

echo "kimi -> $base_url | model: $model | home: $KIMI_CODE_HOME" >&2

exec kimi "${kimi_args[@]}" "$@"
