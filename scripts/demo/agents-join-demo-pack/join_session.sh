#!/usr/bin/env bash
# join_session.sh — run `houmao-mgr agents join` inside the demo tmux session.
#
# Must be run after start_provider.sh.
set -euo pipefail

SESSION_NAME="demo-join-agent"
AGENT_NAME="demo-join-agent"

# Verify the tmux session exists
if ! tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "Error: tmux session '$SESSION_NAME' not found. Run start_provider.sh first." >&2
    exit 1
fi

echo "Running 'houmao-mgr agents join --agent-name $AGENT_NAME' inside tmux session '$SESSION_NAME'..."

# agents join must run from inside the target tmux session.
# We send the command to a new window and wait for it to complete.
tmux new-window -t "$SESSION_NAME" -n join-cmd \
    "pixi run houmao-mgr agents join --agent-name $AGENT_NAME; echo '--- JOIN DONE (exit \$?) ---'; sleep 2"

# Wait for the join command to finish (poll the window; exits when the shell closes)
echo "Waiting for join to complete..."
for i in $(seq 1 30); do
    sleep 1
    if ! tmux list-windows -t "$SESSION_NAME" -F '#{window_name}' 2>/dev/null | grep -q '^join-cmd$'; then
        echo "Join command finished."
        break
    fi
    if [[ $i -eq 30 ]]; then
        echo "Warning: join command did not finish within 30 seconds." >&2
    fi
done
