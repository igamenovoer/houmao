#!/usr/bin/env bash
# stop_agent.sh — gracefully stop the joined agent.
set -euo pipefail

AGENT_NAME="demo-join-agent"
SESSION_NAME="demo-join-agent"

echo "Stopping agent '$AGENT_NAME'..."
pixi run houmao-mgr agents stop --agent-name "$AGENT_NAME" || {
    echo "Warning: 'agents stop' returned non-zero. The session may already be stopped." >&2
}

# Clean up the tmux session if it's still alive
if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "Killing leftover tmux session '$SESSION_NAME'..."
    tmux kill-session -t "$SESSION_NAME"
fi

echo "Agent '$AGENT_NAME' stopped and tmux session cleaned up."
