#!/usr/bin/env bash

set -euo pipefail

usage() {
    cat <<'EOF'
Usage: run_demo.sh --provider claude_code|codex [--output-dir PATH] [--agent-name NAME]

Run the minimal managed-agent launch demo for one supported provider.

Examples:
  scripts/demo/minimal-agent-launch/scripts/run_demo.sh --provider claude_code
  scripts/demo/minimal-agent-launch/scripts/run_demo.sh --provider codex
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${DEMO_ROOT}/../../.." && pwd)"

provider=""
output_dir=""
agent_name=""

while (($# > 0)); do
    case "$1" in
        --provider)
            provider="${2:-}"
            shift 2
            ;;
        --output-dir)
            output_dir="${2:-}"
            shift 2
            ;;
        --agent-name)
            agent_name="${2:-}"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "error: unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [[ -z "${provider}" ]]; then
    echo "error: --provider is required" >&2
    usage >&2
    exit 2
fi

tool=""
provider_executable=""
fixture_auth_source=""

case "${provider}" in
    claude_code)
        tool="claude"
        provider_executable="claude"
        fixture_auth_source="${REPO_ROOT}/tests/fixtures/agents/tools/claude/auth/kimi-coding"
        ;;
    codex)
        tool="codex"
        provider_executable="codex"
        fixture_auth_source="${REPO_ROOT}/tests/fixtures/agents/tools/codex/auth/yunwu-openai"
        ;;
    *)
        echo "error: unsupported provider: ${provider}. Use claude_code or codex." >&2
        exit 2
        ;;
esac

if [[ -z "${output_dir}" ]]; then
    output_dir="${DEMO_ROOT}/outputs/${provider}"
fi

if [[ -z "${agent_name}" ]]; then
    agent_name="minimal-launch-demo-${tool}"
fi

mkdir -p "$(dirname "${output_dir}")"
run_root="$(cd "$(dirname "${output_dir}")" && pwd)/$(basename "${output_dir}")"
workdir="${run_root}/workdir"
generated_agent_def_dir="${workdir}/.agentsys/agents"
runtime_root="${run_root}/runtime"
logs_dir="${run_root}/logs"
inputs_dir="${DEMO_ROOT}/inputs"
prompt_file="${inputs_dir}/prompt.txt"

mkdir -p "${logs_dir}"
rm -rf "${workdir}" "${runtime_root}"
mkdir -p "${workdir}" "${runtime_root}"

require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "error: required command not found: $1" >&2
        exit 1
    fi
}

require_path() {
    if [[ ! -e "$1" ]]; then
        echo "error: required path not found: $1" >&2
        exit 1
    fi
}

run_logged() {
    local label="$1"
    shift
    local logfile="${logs_dir}/${label}.log"
    {
        printf '## %s\n' "${label}"
        printf '$'
        for arg in "$@"; do
            printf ' %q' "${arg}"
        done
        printf '\n'
        "$@"
    } 2>&1 | tee "${logfile}"
}

cleanup_agent() {
    set +e
    (
        cd "${REPO_ROOT}" || exit 1
        export AGENTSYS_AGENT_DEF_DIR="${generated_agent_def_dir}"
        export AGENTSYS_GLOBAL_RUNTIME_DIR="${runtime_root}"
        pixi run houmao-mgr agents stop --agent-name "${agent_name}"
    ) >"${logs_dir}/stop-on-error.log" 2>&1
}

trap cleanup_agent ERR

require_command pixi
require_command tmux
require_command "${provider_executable}"
require_path "${inputs_dir}/agents"
require_path "${prompt_file}"

if [[ ! -d "${fixture_auth_source}" ]]; then
    echo "error: fixture auth bundle missing for ${provider}: ${fixture_auth_source}" >&2
    echo "restore the local fixture auth bundle before running this demo" >&2
    exit 1
fi

mkdir -p "${generated_agent_def_dir}"
cp -R "${inputs_dir}/agents/." "${generated_agent_def_dir}/"
mkdir -p \
    "${generated_agent_def_dir}/tools/claude/auth" \
    "${generated_agent_def_dir}/tools/codex/auth"
ln -s "${fixture_auth_source}" "${generated_agent_def_dir}/tools/${tool}/auth/default"

cat >"${run_root}/summary.json" <<EOF
{
  "provider": "${provider}",
  "tool": "${tool}",
  "agent_name": "${agent_name}",
  "fixture_auth_source": "${fixture_auth_source}",
  "generated_agent_def_dir": "${generated_agent_def_dir}",
  "runtime_root": "${runtime_root}",
  "prompt_file": "${prompt_file}"
}
EOF

export AGENTSYS_AGENT_DEF_DIR="${generated_agent_def_dir}"
export AGENTSYS_GLOBAL_RUNTIME_DIR="${runtime_root}"

(
    cd "${REPO_ROOT}"
    run_logged launch \
        pixi run houmao-mgr agents launch \
        --agents minimal-launch \
        --provider "${provider}" \
        --agent-name "${agent_name}" \
        --headless \
        --yolo
    run_logged prompt \
        pixi run houmao-mgr agents prompt \
        --agent-name "${agent_name}" \
        --prompt "$(cat "${prompt_file}")"
    sleep 2
    run_logged state \
        pixi run houmao-mgr agents state \
        --agent-name "${agent_name}"
    run_logged stop \
        pixi run houmao-mgr agents stop \
        --agent-name "${agent_name}"
)

trap - ERR

printf '\nDemo complete.\n'
printf 'provider=%s\n' "${provider}"
printf 'agent_name=%s\n' "${agent_name}"
printf 'output_root=%s\n' "${run_root}"
printf 'logs=%s\n' "${logs_dir}"
