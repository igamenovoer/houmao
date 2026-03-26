# Serverless `houmao-mgr` Run Log: `james` Launch Terminal Handoff Failure

## Date
2026-03-26 10:13:28 UTC

## Status
Issue observed

## Scenario
Launch one serverless interactive Claude Code agent through `houmao-mgr` without `houmao-server`.

## Command
```bash
AGENTSYS_AGENT_DEF_DIR="$PWD/tests/fixtures/agents" \
pixi run houmao-mgr agents launch \
  --agents projection-demo \
  --provider claude_code \
  --agent-name james \
  --session-name james \
  --yolo
```

## Observed Output
```text
Managed agent launch complete:
agent_name=james
agent_id=b4cc344d25a2efe540adbf2678e2304c
tmux_session_name=james
manifest_path=/home/huangzhe/.houmao/runtime/sessions/local_interactive/local_interactive-20260326-101307Z-d5209044/manifest.json
open terminal failed: not a terminal
```

## Follow-Up Verification
The managed agent did launch successfully despite the terminal handoff failure.

### Session Check
```bash
tmux has-session -t james && echo alive
```

Observed:

```text
alive
```

### Managed-Agent State Check
```bash
AGENTSYS_AGENT_DEF_DIR="$PWD/tests/fixtures/agents" \
pixi run houmao-mgr agents state --agent-name james
```

Observed key fields:

- `availability: "available"`
- `identity.agent_name: "james"`
- `identity.tmux_session_name: "james"`
- `identity.tool: "claude"`
- `turn.phase: "ready"`

## Impact
The serverless interactive launch path can create the tmux-backed Claude agent successfully, but the post-launch operator handoff tries to open a terminal in an environment that is not a TTY and emits:

```text
open terminal failed: not a terminal
```

This is a user-visible UX failure for non-interactive callers, scripted test runners, and agent-driven launch flows. The launch itself succeeds, but the command exits with an avoidable terminal-opening error message.

## Notes
- This issue was observed from the repository root at `/data1/huangzhe/code/houmao`.
- No `houmao-server` was involved in this run.
- Effective agent-definition root: `tests/fixtures/agents`.
