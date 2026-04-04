#!/usr/bin/env bash
# start_provider.sh — create a tmux session and launch a provider TUI.
#
# Usage: start_provider.sh <provider>
#   provider: claude | codex | gemini
set -euo pipefail

PROVIDER="${1:?Usage: start_provider.sh <provider>}"
SESSION_NAME="demo-join-agent"

case "$PROVIDER" in
    claude)  CMD="claude" ;;
    codex)   CMD="codex"  ;;
    gemini)  CMD="gemini" ;;
    *)
        echo "Error: unsupported provider '$PROVIDER'." >&2
        exit 1
        ;;
esac

# Ensure the provider binary is available
if ! command -v "$CMD" &>/dev/null; then
    echo "Error: '$CMD' is not on PATH. Install the provider CLI first." >&2
    exit 1
fi

# Kill any leftover session from a previous run
tmux kill-session -t "$SESSION_NAME" 2>/dev/null || true

# Create a detached session running the provider TUI
tmux new-session -d -s "$SESSION_NAME" -x 200 -y 50 "$CMD"
echo "tmux session '$SESSION_NAME' created with '$CMD' in window 0, pane 0."
