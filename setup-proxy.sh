#!/usr/bin/env bash
# Usage:
#   source ~/setup-proxy.sh
#
# Sets HTTP(S) proxy env vars to the first reachable proxy from
# PROXY_CANDIDATE_LIST (comma-separated URLs).
# You can override PROXY_CANDIDATE_LIST by passing:
#   source ~/setup-proxy.sh --proxy-candidate-list "proxy1,proxy2"
#
# PROXY_CANDIDATE_LIST format:
# - Comma-separated list of URLs or host[:port] entries.
# - Supported schemes: http://, socks5:// (or no scheme -> assumed http://).
# - Missing port -> assumed 7890.
#
# If PROXY_CANDIDATE_LIST is unset/empty, probes only 127.0.0.1:7890.
#
# Docker behavior:
# - If PROXY_CANDIDATE_LIST is unset/empty and we detect we're running inside a
#   container, the default probe list expands to:
#     - 127.0.0.1:7890
#     - host.docker.internal:7890
#     - <container default gateway IP>:7890 (parsed from /proc/net/route)
#
# Note: On many Linux Docker setups, host.docker.internal is NOT available by
# default. You can enable it per-container with:
#   docker run --add-host host.docker.internal:host-gateway ...
# If no candidate is reachable, leaves the current environment unchanged.

# If this script is executed (not sourced), instruct the user and exit.
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  cat >&2 <<'EOF'
Usage:
  source ~/setup-proxy.sh [--proxy-candidate-list "a:7890,b:7890"]

Behavior:
  - Picks the first reachable proxy from the candidate list.
  - If --proxy-candidate-list is provided, it overrides PROXY_CANDIDATE_LIST.
  - Otherwise uses PROXY_CANDIDATE_LIST (comma-separated).
  - If neither is set, probes only 127.0.0.1:7890.

Docker behavior:
  - If no candidate list is provided and the script detects it's running inside
    a container, the default probe list expands to include:
      - 127.0.0.1:7890
      - host.docker.internal:7890
      - <container default gateway IP>:7890
  - On many Linux Docker setups, host.docker.internal is NOT available by
    default; you can enable it per-container with:
      docker run --add-host host.docker.internal:host-gateway ...

Candidate format:
  - Comma-separated entries: URL or host[:port]
  - Supported schemes: http://, socks5://
  - Missing scheme defaults to http://
  - Missing port defaults to 7890
EOF
  exit 2
fi

_default_proxy_port="7890"

_log() {
  echo "[setup-proxy] $*" >&2
}

_in_docker() {
  # Common indicators for Docker/containers.
  [[ -f "/.dockerenv" ]] && return 0
  [[ -r "/proc/1/cgroup" ]] && grep -qaE '(docker|containerd|kubepods)' /proc/1/cgroup && return 0
  return 1
}

_hex_le_to_ipv4() {
  # Convert an 8-hex-digit little-endian IPv4 (as in /proc/net/route) to dotted quad.
  local h="${1}"
  [[ "${#h}" -ne 8 ]] && return 1
  local b1="${h:6:2}" b2="${h:4:2}" b3="${h:2:2}" b4="${h:0:2}"
  printf '%d.%d.%d.%d' "$((16#${b1}))" "$((16#${b2}))" "$((16#${b3}))" "$((16#${b4}))"
}

_docker_default_gateway_ipv4() {
  # Best-effort: parse /proc/net/route for the default route gateway.
  [[ -r /proc/net/route ]] || return 1
  local line iface dest gw flags rest
  # Skip header
  while IFS=$'\t ' read -r iface dest gw flags rest; do
    [[ -z "${iface}" || "${iface}" == "Iface" ]] && continue
    [[ "${dest}" != "00000000" ]] && continue
    local ip
    ip="$(_hex_le_to_ipv4 "${gw}")" || continue
    [[ -n "${ip}" ]] || continue
    printf '%s' "${ip}"
    return 0
  done < /proc/net/route
  return 1
}

_proxy_candidate_list_arg=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --proxy-candidate-list)
      shift
      if [[ $# -lt 1 || -z "${1}" ]]; then
        echo "Missing value for --proxy-candidate-list" >&2
        return 2
      fi
      _proxy_candidate_list_arg="$1"
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      echo "Usage: source ~/setup-proxy.sh [--proxy-candidate-list \"a:7890,b:7890\"]" >&2
      return 2
      ;;
  esac
done

_is_empty_or_unset() {
  [[ -z "${1-}" ]]
}

_normalize_candidates() {
  # Emits one normalized proxy URL per line.
  # Normalized form: http://host:port or socks5://host:port
  local raw_list
  local raw_source
  if ! _is_empty_or_unset "${_proxy_candidate_list_arg-}"; then
    raw_list="${_proxy_candidate_list_arg}"
    raw_source="--proxy-candidate-list"
  elif _is_empty_or_unset "${PROXY_CANDIDATE_LIST-}"; then
    if _in_docker; then
      raw_list="127.0.0.1:${_default_proxy_port},host.docker.internal:${_default_proxy_port}"
      local gw
      gw="$(_docker_default_gateway_ipv4 2>/dev/null || true)"
      if [[ -n "${gw}" ]]; then
        raw_list+="${raw_list:+,}${gw}:${_default_proxy_port}"
      fi
      raw_source="default (docker)"
    else
      raw_list="127.0.0.1:${_default_proxy_port}"
      raw_source="default"
    fi
  else
    raw_list="${PROXY_CANDIDATE_LIST}"
    raw_source="PROXY_CANDIDATE_LIST"
  fi

  _log "[INFO] Candidate source: ${raw_source}"
  _log "[INFO] Raw candidates: ${raw_list}"

  # Pure-bash normalization.
  local IFS=','
  local item
  local -A _seen
  for item in ${raw_list}; do
    item="${item#${item%%[![:space:]]*}}" # ltrim
    item="${item%${item##*[![:space:]]}}" # rtrim
    [[ -z "${item}" ]] && continue

    local scheme="http"
    local rest="${item}"
    if [[ "${item}" == *"://"* ]]; then
      scheme="${item%%://*}"
      rest="${item#*://}"
      scheme="${scheme,,}"
    fi
    [[ "${scheme}" != "http" && "${scheme}" != "socks5" ]] && continue

    # Strip path/query/fragment.
    rest="${rest%%/*}"
    rest="${rest%%\?*}"
    rest="${rest%%#*}"

    # Strip userinfo.
    rest="${rest#*@}"

    rest="${rest#${rest%%[![:space:]]*}}" # ltrim
    rest="${rest%${rest##*[![:space:]]}}" # rtrim
    [[ -z "${rest}" ]] && continue

    local host=""
    local port="${_default_proxy_port}"
    # Support bracketed IPv6: [::1]:7890 (optional port)
    if [[ "${rest}" == \[*\]* ]]; then
      # rest like: [host] or [host]:port
      host="${rest#\[}"
      host="${host%%\]*}"
      if [[ "${rest}" == \[*\]:* ]]; then
        local maybe_port="${rest##*:}"
        [[ "${maybe_port}" =~ ^[0-9]+$ ]] && port="${maybe_port}"
      fi
      [[ -z "${host}" ]] && continue
      local normalized="${scheme}://[${host}]:${port}"
      if [[ -z "${_seen[${normalized}]+x}" ]]; then
        _seen["${normalized}"]=1
        printf '%s\n' "${normalized}"
      fi
      continue
    fi

    host="${rest}"
    if [[ "${rest}" == *":"* ]]; then
      local maybe_port="${rest##*:}"
      local maybe_host="${rest%:*}"
      if [[ -n "${maybe_host}" && "${maybe_port}" =~ ^[0-9]+$ ]]; then
        host="${maybe_host}"
        port="${maybe_port}"
      fi
    fi
    [[ -z "${host}" ]] && continue
    local normalized="${scheme}://${host}:${port}"
    if [[ -z "${_seen[${normalized}]+x}" ]]; then
      _seen["${normalized}"]=1
      printf '%s\n' "${normalized}"
    fi
  done
}

_extract_host_port() {
  # Input: normalized URL (http://host:port or socks5://host:port)
  # Output: host<space>port
  local url="${1}"
  local rest="${url#*://}"
  local hostport="${rest%%/*}"
  if [[ "${hostport}" == \[*\]::* ]]; then
    # [::1]:7890
    local host="${hostport%%]*}"
    host="${host#[}"
    local port="${hostport##*:}"
    printf '%s %s\n' "${host}" "${port}"
    return 0
  fi
  local host="${hostport%:*}"
  local port="${hostport##*:}"
  printf '%s %s\n' "${host}" "${port}"
}

# Return success (0) if we can open a TCP connection to host:port quickly.
_proxy_reachable_host_port() {
  local host="${1}"
  local port="${2}"

  # Fallback (requires bash with /dev/tcp support).
  if command -v timeout >/dev/null 2>&1; then
    timeout 2 bash -lc "cat < /dev/null > /dev/tcp/${host}/${port}" >/dev/null 2>&1
    return $?
  fi

  # Last-resort attempt without timeout.
  bash -lc "cat < /dev/null > /dev/tcp/${host}/${port}" >/dev/null 2>&1
}

_selected_proxy_url=""

while IFS= read -r candidate_url; do
  [[ -z "${candidate_url}" ]] && continue
  _log "[TRY] ${candidate_url}"
  read -r _host _port < <(_extract_host_port "${candidate_url}")
  if _proxy_reachable_host_port "${_host}" "${_port}"; then
    _selected_proxy_url="${candidate_url}"
    _log "[OK] ${candidate_url}"
    break
  fi
  _log "[FAILED] ${candidate_url}"
done < <(_normalize_candidates)

if [[ -z "${_selected_proxy_url}" ]]; then
  echo "No reachable proxy found; leaving environment unchanged." >&2
  unset _proxy_candidate_list_arg
  return 0
fi

_log "[SELECTED] ${_selected_proxy_url}"

# Set both lowercase and uppercase variants used by many tools.
export http_proxy="${_selected_proxy_url}"
export https_proxy="${_selected_proxy_url}"
export HTTP_PROXY="${_selected_proxy_url}"
export HTTPS_PROXY="${_selected_proxy_url}"

# (Optional) some tools honor this as well.
export all_proxy="${_selected_proxy_url}"
export ALL_PROXY="${_selected_proxy_url}"

echo "Proxy enabled: ${_selected_proxy_url}" >&2

unset _proxy_candidate_list_arg
