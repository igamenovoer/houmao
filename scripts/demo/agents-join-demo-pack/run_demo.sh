#!/usr/bin/env bash
# run_demo.sh — orchestrate the agents-join demo end-to-end.
#
# Usage:
#   scripts/demo/agents-join-demo-pack/run_demo.sh [--provider claude|codex|gemini]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEMO_ROOT="tmp/demo/agents-join-demo-pack"
PROVIDER="claude"

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --provider)
            PROVIDER="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--provider claude|codex|gemini]"
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 1
            ;;
    esac
done

case "$PROVIDER" in
    claude|codex|gemini) ;;
    *)
        echo "Error: unsupported provider '$PROVIDER'. Use one of: claude, codex, gemini." >&2
        exit 1
        ;;
esac

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
section() {
    echo ""
    echo "============================================================"
    echo "  $1"
    echo "============================================================"
    echo ""
}

cleanup() {
    echo ""
    echo "Cleaning up tmux session demo-join-agent (if still alive)..."
    tmux kill-session -t demo-join-agent 2>/dev/null || true
}
trap cleanup EXIT

# ---------------------------------------------------------------------------
# Prepare demo root
# ---------------------------------------------------------------------------
mkdir -p "$DEMO_ROOT"

# ---------------------------------------------------------------------------
# Step 1: Start the provider TUI inside a tmux session
# ---------------------------------------------------------------------------
section "Step 1 / 4 — Start provider ($PROVIDER) in tmux session"
bash "$SCRIPT_DIR/start_provider.sh" "$PROVIDER"
echo "Provider '$PROVIDER' is running in tmux session 'demo-join-agent'."
echo "Waiting 3 seconds for TUI initialization..."
sleep 3

# ---------------------------------------------------------------------------
# Step 2: Join the session
# ---------------------------------------------------------------------------
section "Step 2 / 4 — Join the running session with houmao-mgr agents join"
bash "$SCRIPT_DIR/join_session.sh"

# ---------------------------------------------------------------------------
# Step 3: Inspect state
# ---------------------------------------------------------------------------
section "Step 3 / 4 — Inspect agent state"
bash "$SCRIPT_DIR/inspect_state.sh"

# ---------------------------------------------------------------------------
# Step 4: Stop the agent
# ---------------------------------------------------------------------------
section "Step 4 / 4 — Stop the joined agent"
bash "$SCRIPT_DIR/stop_agent.sh"

section "Demo complete!"
echo "The agents-join workflow ran successfully with provider '$PROVIDER'."
