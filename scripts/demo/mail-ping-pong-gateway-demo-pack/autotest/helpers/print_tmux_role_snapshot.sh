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

PANE_TARGET="$(
    tmux list-panes -t "$SESSION_NAME" -F '#{session_name}:#{window_index}.#{pane_index} #{window_active} #{pane_active}' \
        | awk '$2 == "1" && $3 == "1" { print $1; exit }'
)"
if [[ -z "$PANE_TARGET" ]]; then
    PANE_TARGET="$(tmux list-panes -t "$SESSION_NAME" -F '#{session_name}:#{window_index}.#{pane_index}' | head -n1)"
fi
if [[ -z "$PANE_TARGET" ]]; then
    echo "no panes found for tmux session: $SESSION_NAME" >&2
    exit 1
fi

echo "=== $ROLE_NAME tmux snapshot ($SESSION_NAME) ==="
tmux capture-pane -p -t "$PANE_TARGET" -S "-$LINES"
echo
echo "Attach from another terminal if you want a live view:"
echo "  tmux attach-session -t $SESSION_NAME"
