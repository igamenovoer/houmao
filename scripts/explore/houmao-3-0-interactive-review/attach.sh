#!/usr/bin/env bash
# Attach to the isolated Houmao 3.0 campaign tmux session without touching the default server.
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/../../.." && pwd)"
run_root="${HOUMAO_ITER1_RUN_ROOT:-$repo_root/tmp/houmao-30-iter1}"
sock="$run_root/tsock/tmux-$(id -u)/default"

print_only=0
arm=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --print)
      print_only=1
      shift
      ;;
    -h|--help)
      echo "usage: $0 [b1|b2|a1|a2] [--print]"
      exit 0
      ;;
    *)
      arm="$1"
      shift
      ;;
  esac
done

target=""
if [[ -n "$arm" ]]; then
  state_file="$run_root/arms/$arm/arm-state.json"
  if [[ -f "$state_file" ]]; then
    target="$(jq -r '.session_name // empty' "$state_file")"
  fi
  if [[ -z "$target" ]]; then
    echo "error: no launched session recorded for arm '$arm' in $state_file" >&2
    exit 1
  fi
fi

if [[ "$print_only" == "1" ]]; then
  if [[ -n "$target" ]]; then
    printf 'env -u TMUX -u TMUX_PANE tmux -S %q attach -t %q\n' "$sock" "$target"
  else
    printf 'env -u TMUX -u TMUX_PANE tmux -S %q attach\n' "$sock"
  fi
  exit 0
fi

if [[ -n "$target" ]]; then
  exec env -u TMUX -u TMUX_PANE tmux -S "$sock" attach -t "$target"
fi
exec env -u TMUX -u TMUX_PANE tmux -S "$sock" attach
