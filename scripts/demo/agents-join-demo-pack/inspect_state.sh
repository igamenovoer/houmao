#!/usr/bin/env bash
# inspect_state.sh — query agent state after joining.
set -euo pipefail

AGENT_NAME="demo-join-agent"

echo "Querying agent state for '$AGENT_NAME'..."
echo ""

pixi run houmao-mgr agents state --agent-name "$AGENT_NAME" || {
    echo "Error: 'agents state' failed. Is the agent joined?" >&2
    exit 1
}
