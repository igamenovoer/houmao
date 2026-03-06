#!/bin/bash

# Save original shell options to restore at the end (for sourcing)
_original_shell_opts=$(set +o)

_is_sourced() {
	[[ "${BASH_SOURCE[0]}" != "${0}" ]]
}

_return_or_exit() {
	local code="$1"
	if _is_sourced; then
		return "$code"
	fi
	exit "$code"
}

usage() {
	cat <<'EOF'
Usage: setup-envs.sh

Behavior:
	- Sets CODEX_HOME (only if $PWD/.codex exists when sourced).
	- If any proxy env vars are already set, keeps them unchanged.
	- Otherwise, delegates proxy discovery to ./setup-proxy.sh in the same
	  directory. See that script for Docker/container probing behavior and how to
	  override candidates via PROXY_CANDIDATE_LIST.

Options:
	-h, --help Show this help message and exit
EOF
}

# This script is intended to be sourced so it can modify the current shell.
if ! _is_sourced; then
	echo "Warning: this script should be sourced (not executed)." >&2
	echo "" >&2
	echo "When sourced, it will:" >&2
	echo "" >&2
	usage >&2
	echo "" >&2
	echo "Example:" >&2
	echo "  source ./setup-envs.sh" >&2
	exit 2
fi

SCRIPT_DIR="$(cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

codex_status=""
_codex_dir="${PWD}/.codex"
if [[ -d "${_codex_dir}" ]]; then
	# Prefer an absolute path for CODEX_HOME.
	if command -v realpath >/dev/null 2>&1; then
		CODEX_HOME="$(realpath "${_codex_dir}" 2>/dev/null || printf '%s\n' "${_codex_dir}")"
	else
		CODEX_HOME="$(cd -- "${_codex_dir}" && pwd -P)"
	fi
	export CODEX_HOME
	codex_status="set to ${CODEX_HOME}"
else
	if [[ -n "${CODEX_HOME:-}" ]]; then
		codex_status="kept (pre-existing: ${CODEX_HOME})"
	else
		codex_status="not set (no ${_codex_dir} directory)"
	fi
fi

while (($# > 0)); do
	case "$1" in
		-h|--help)
			usage
			_return_or_exit 0
			;;
		*)
			echo "Error: Unknown option: $1" >&2
			usage
			_return_or_exit 1
			;;
	esac
	shift
done

probe_proxy_via_setup_proxy() {
	local helper_script="${SCRIPT_DIR}/setup-proxy.sh"
	if [[ ! -f "$helper_script" ]]; then
		echo "Error: proxy helper not found: $helper_script" >&2
		echo "Hint: expected setup-proxy.sh to be alongside setup-envs.sh" >&2
		return 2
	fi

	# Source the helper so it can export proxy env vars into this process.
	# It leaves the environment unchanged if no reachable proxy is found.
	# shellcheck disable=SC1090
	source "$helper_script"
}

proxy_status=""

# Respect existing proxy configuration; otherwise delegate to setup-proxy.sh.
if [[ -n "${HTTP_PROXY:-}" || -n "${HTTPS_PROXY:-}" || -n "${http_proxy:-}" || -n "${https_proxy:-}" ]]; then
	proxy_status="kept (pre-existing)"
else
	if ! probe_proxy_via_setup_proxy; then
		echo "Error: failed to discover proxy (setup-proxy.sh missing or errored)." >&2
		eval "$_original_shell_opts"
		unset _original_shell_opts
		return 2
	fi
	if [[ -n "${HTTP_PROXY:-}" || -n "${HTTPS_PROXY:-}" || -n "${http_proxy:-}" || -n "${https_proxy:-}" ]]; then
		proxy_status="detected and set to ${HTTP_PROXY:-${http_proxy:-<unknown>}}"
	else
		proxy_status="not set (no proxy detected)"
	fi
fi

# Print all environment variables set by this script
echo ""
echo "========================================="
echo "Environment variables configured:"
echo "========================================="
echo "CODEX_HOME status: ${codex_status}"
echo "CODEX_HOME = ${CODEX_HOME:-<not set>}"
echo ""
echo "Proxy status: $proxy_status"
if [[ -n "${HTTP_PROXY:-}" || -n "${HTTPS_PROXY:-}" || -n "${http_proxy:-}" || -n "${https_proxy:-}" ]]; then
	echo "  HTTP_PROXY  = ${HTTP_PROXY:-<not set>}"
	echo "  HTTPS_PROXY = ${HTTPS_PROXY:-<not set>}"
	echo "  http_proxy  = ${http_proxy:-<not set>}"
	echo "  https_proxy = ${https_proxy:-<not set>}"
else
	echo "  (no proxy variables set)"
fi
echo "========================================="

# Restore original shell options (important when sourced)
eval "$_original_shell_opts"
unset _original_shell_opts
