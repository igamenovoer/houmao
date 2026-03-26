# Serverless `houmao-mgr` Run Log: `james` Prompt Accepted But TUI Appears Stuck Active

## Date
2026-03-26 10:47:38 UTC

## Status
Issue observed

## Scenario
Send one prompt to the already-running serverless interactive Claude agent `james` through `houmao-mgr agents prompt`.

## Command
```bash
AGENTSYS_AGENT_DEF_DIR="$PWD/tests/fixtures/agents" \
pixi run houmao-mgr agents prompt \
  --agent-name james \
  --prompt 'Reply with exactly JAMES_OK and nothing else.'
```

## Immediate CLI Result
```json
{
  "detail": "Prompt submitted through the local runtime controller.",
  "disposition": "accepted",
  "headless_turn_id": null,
  "headless_turn_index": null,
  "request_id": "prompt-20260326T104640Z-3a8d769767",
  "request_kind": "submit_prompt",
  "success": true,
  "tracked_agent_id": "b4cc344d25a2efe540adbf2678e2304c"
}
```

## Follow-Up Observations

### Tmux Pane Capture
After repeated follow-up checks, the live pane still showed the prompt text but no visible completion:

```text
❯ Reply with exactly JAMES_OK and nothing else.

✢ Sock-hopping… (58s)
  ⎿  Tip: Use /btw to ask a quick side question without interrupting Claude's current work
```

The pane also continued to show:

```text
⏵⏵ bypass permissions on (shift+tab to cycle) · esc to interrupt
```

### Managed-Agent State
Repeated `houmao-mgr agents state --agent-name james` checks showed:

- `availability: "available"`
- `turn.phase: "active"`
- `turn.active_turn_id: "tui-anchor:b4cc344d25a2efe540adbf2678e2304c"`
- `last_turn.result: "none"`

The state did not return to `ready` during the observation window.

## Impact
The serverless post-launch prompt path appears to accept and inject the prompt into the live Claude TUI, but the interactive session did not visibly complete the request during the observed window and remained in an `active` state.

This suggests a gap between prompt admission and reliable completion for the local interactive Claude control path, or a provider-side stall that Houmao currently does not surface clearly.

## Notes
- The target agent was addressed by the raw creation-time name `james`.
- No `houmao-server` was involved.
- The tmux pane confirmed that the exact prompt text reached the interactive Claude session.
