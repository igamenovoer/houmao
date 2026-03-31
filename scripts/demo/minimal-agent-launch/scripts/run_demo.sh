#!/usr/bin/env bash

set -euo pipefail

usage() {
    cat <<'EOF'
Usage: run_demo.sh --provider claude_code|codex [--headless] [--output-dir PATH] [--agent-name NAME]

Run the minimal managed-agent launch demo for one supported provider.
Default behavior launches a TUI agent. Use --headless for the headless lane.

Examples:
  scripts/demo/minimal-agent-launch/scripts/run_demo.sh --provider claude_code
  scripts/demo/minimal-agent-launch/scripts/run_demo.sh --provider claude_code --headless
  scripts/demo/minimal-agent-launch/scripts/run_demo.sh --provider codex
  scripts/demo/minimal-agent-launch/scripts/run_demo.sh --provider codex --headless
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${DEMO_ROOT}/../../.." && pwd)"

provider=""
headless="false"
output_dir=""
agent_name=""

while (($# > 0)); do
    case "$1" in
        --provider)
            provider="${2:-}"
            shift 2
            ;;
        --headless)
            headless="true"
            shift
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
launch_mode=""
transport=""

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

if [[ "${headless}" == "true" ]]; then
    launch_mode="headless"
    transport="headless"
else
    launch_mode="tui"
    transport="tui"
fi

if [[ -z "${output_dir}" ]]; then
    if [[ "${transport}" == "headless" ]]; then
        output_dir="${DEMO_ROOT}/outputs/${provider}-headless"
    else
        output_dir="${DEMO_ROOT}/outputs/${provider}"
    fi
fi

if [[ -z "${agent_name}" ]]; then
    if [[ "${transport}" == "headless" ]]; then
        agent_name="minimal-launch-demo-${tool}-headless"
    else
        agent_name="minimal-launch-demo-${tool}"
    fi
fi

mkdir -p "$(dirname "${output_dir}")"
run_root="$(cd "$(dirname "${output_dir}")" && pwd)/$(basename "${output_dir}")"
workdir="${run_root}/workdir"
generated_agent_def_dir="${workdir}/.houmao/agents"
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

extract_log_field() {
    local key="$1"
    local logfile="$2"

    if [[ ! -f "${logfile}" ]]; then
        return 0
    fi

    awk -F= -v key="${key}" '$1 == key { print substr($0, length(key) + 2); exit }' "${logfile}"
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

run_best_effort_logged() {
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
    } >"${logfile}" 2>&1 || true
}

cleanup_agent_on_error() {
    set +e
    (
        cd "${REPO_ROOT}" || exit 1
        export HOUMAO_AGENT_DEF_DIR="${generated_agent_def_dir}"
        export HOUMAO_GLOBAL_RUNTIME_DIR="${runtime_root}"
        pixi run houmao-mgr agents stop --agent-name "${agent_name}"
    ) >"${logs_dir}/stop-on-error.log" 2>&1
}

trap cleanup_agent_on_error ERR

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

export HOUMAO_AGENT_DEF_DIR="${generated_agent_def_dir}"
export HOUMAO_GLOBAL_RUNTIME_DIR="${runtime_root}"

(
    cd "${REPO_ROOT}"
    run_best_effort_logged preflight-stop \
        pixi run houmao-mgr agents stop \
        --agent-name "${agent_name}"

    launch_args=(
        pixi run houmao-mgr agents launch
        --agents minimal-launch
        --provider "${provider}"
        --agent-name "${agent_name}"
        --yolo
    )
    if [[ "${headless}" == "true" ]]; then
        launch_args+=(--headless)
    fi

    run_logged launch \
        "${launch_args[@]}"

    sleep 2

    if [[ "${headless}" == "true" ]]; then
        run_logged prompt \
            pixi run houmao-mgr agents prompt \
            --agent-name "${agent_name}" \
            --prompt "$(cat "${prompt_file}")"
        sleep 2
    fi

    run_logged state \
        pixi run houmao-mgr agents state \
        --agent-name "${agent_name}"

    if [[ "${headless}" == "true" ]]; then
        run_logged stop \
            pixi run houmao-mgr agents stop \
            --agent-name "${agent_name}"
    fi
)

trap - ERR

tmux_session_name="$(extract_log_field tmux_session_name "${logs_dir}/launch.log")"
terminal_handoff="$(extract_log_field terminal_handoff "${logs_dir}/launch.log")"
attach_command="$(extract_log_field attach_command "${logs_dir}/launch.log")"

cat >"${run_root}/summary.json" <<EOF
{
  "provider": "${provider}",
  "tool": "${tool}",
  "transport": "${transport}",
  "launch_mode": "${launch_mode}",
  "agent_name": "${agent_name}",
  "fixture_auth_source": "${fixture_auth_source}",
  "generated_agent_def_dir": "${generated_agent_def_dir}",
  "runtime_root": "${runtime_root}",
  "prompt_file": "${prompt_file}",
  "tmux_session_name": "${tmux_session_name}",
  "terminal_handoff": "${terminal_handoff}",
  "attach_command": "${attach_command}"
}
EOF

printf '\nDemo complete.\n'
printf 'provider=%s\n' "${provider}"
printf 'transport=%s\n' "${transport}"
printf 'headless=%s\n' "${headless}"
printf 'agent_name=%s\n' "${agent_name}"
printf 'output_root=%s\n' "${run_root}"
printf 'logs=%s\n' "${logs_dir}"
if [[ "${transport}" == "tui" ]]; then
    printf 'tmux_session_name=%s\n' "${tmux_session_name}"
    printf 'terminal_handoff=%s\n' "${terminal_handoff}"
    printf 'attach_command=%s\n' "${attach_command}"
    printf 'next_stop_command=%s\n' "pixi run houmao-mgr agents stop --agent-name ${agent_name}"
fi
