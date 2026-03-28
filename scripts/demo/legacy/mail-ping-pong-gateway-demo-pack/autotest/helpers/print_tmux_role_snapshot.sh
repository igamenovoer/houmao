#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 || $# -gt 3 ]]; then
    echo "usage: print_tmux_role_snapshot.sh <demo_state.json> <initiator|responder> [lines]" >&2
    exit 2
fi

STATE_PATH="$1"
ROLE_NAME="$2"
LINES="${3:-80}"

if [[ ! -f "$STATE_PATH" ]]; then
    echo "demo state file not found: $STATE_PATH" >&2
    exit 1
fi

SESSION_NAME="$(
    pixi run python - "$STATE_PATH" "$ROLE_NAME" <<'PY'
import json
import sys
from pathlib import Path

state_path = Path(sys.argv[1]).resolve()
role_name = sys.argv[2]
payload = json.loads(state_path.read_text(encoding="utf-8"))
if role_name not in {"initiator", "responder"}:
    raise SystemExit(f"unknown role: {role_name}")
print(payload[role_name]["tmux_session_name"])
PY
)"

if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "tmux session not found: $SESSION_NAME" >&2
    exit 1
fi

WINDOW_TARGET="$SESSION_NAME:0"
PANE_TARGET="$(tmux list-panes -t "$WINDOW_TARGET" -F '#{session_name}:#{window_index}.#{pane_index}' 2>/dev/null | head -n1)"
if [[ -z "$PANE_TARGET" ]]; then
    echo "stable agent window not found: $WINDOW_TARGET" >&2
    exit 1
fi

echo "=== $ROLE_NAME tmux snapshot ($WINDOW_TARGET agent) ==="
tmux capture-pane -p -t "$PANE_TARGET" -S "-$LINES"
echo
echo "Attach from another terminal if you want a live view:"
echo "  tmux attach-session -t $SESSION_NAME \\; select-window -t $WINDOW_TARGET"
