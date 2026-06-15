#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

if ! command -v bun >/dev/null 2>&1; then
  echo "Bun is required for the real tmux workbench smoke." >&2
  exit 1
fi

if [[ -z "${HMWB_TMUX_SESSION:-}" ]]; then
  echo "Set HMWB_TMUX_SESSION to the real tmux session name to attach." >&2
  exit 1
fi

cd "$REPO_ROOT/apps/ag-ui-workbench"
exec bun run "$REPO_ROOT/scripts/demo/ag-ui-real-tmux-workbench-smoke/real_tmux_smoke.ts"
