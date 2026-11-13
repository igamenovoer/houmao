#!/usr/bin/env bash
# Launch Codex against the H20-hosted Qwen3.8 Responses API.
#
# Codex has no config-file path flag; it reads $CODEX_HOME/config.toml. This
# wrapper installs tests/codex-config.toml into an isolated Codex home and
# forwards every argument to `codex`.
#
# Overrides:
#   CODEX_QWEN_HOME        isolated Codex home (default: tmp/.../codex-qwen)
#   QWEN_API_KEY           provider key (default: EMPTY)
#   CODEX_SKIP_PERMISSIONS set to 0 to keep approvals and the sandbox
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/../../../.." && pwd)"
config_template="$script_dir/codex-config.toml"

if [[ ! -f "$config_template" ]]; then
  echo "error: missing $config_template" >&2
  exit 1
fi

if ! command -v codex >/dev/null 2>&1; then
  echo "error: codex is not on PATH" >&2
  exit 1
fi

base_url="$(grep -m1 '^base_url = ' "$config_template" | cut -d'"' -f2 || true)"
if [[ -n "$base_url" ]] && command -v curl >/dev/null 2>&1; then
  if ! curl -fsS -m 5 "${base_url%/}/models" >/dev/null; then
    echo "error: no Responses API server at $base_url (start the H20 tunnel/service first)" >&2
    exit 1
  fi
fi

# Codex reads only $CODEX_HOME/config.toml; install the checked-in config there.
codex_home="${CODEX_QWEN_HOME:-$repo_root/tmp/expose-agent-usage-records/codex-qwen}"
mkdir -p "$codex_home"
cp "$config_template" "$codex_home/config.toml"
export CODEX_HOME="$codex_home"
export QWEN_API_KEY="${QWEN_API_KEY:-EMPTY}"

echo "codex -> $base_url | config: $codex_home/config.toml" >&2

codex_args=()
if [[ "${CODEX_SKIP_PERMISSIONS:-1}" != "0" ]]; then
  codex_args+=(--dangerously-bypass-approvals-and-sandbox)
fi

exec codex "${codex_args[@]}" "$@"
