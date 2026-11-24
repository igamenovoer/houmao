# Inspect the Live Pane or TUI State

## Workflow

1. Use the parent's launcher and resolve the explicit agent or verified self from managed identity.
2. Read scoped summary state. Use managed detail or active TUI observations for the requested evidence. For headless output, use [Logs](logs.md).
3. If the caller needs the actual pane or managed observations are insufficient, use **Verified Local Tmux**. Attach only when the caller asks to attach.
4. Report the identity, observation source, and any unavailable evidence.

If the task does not fit these steps, use the native planning tool to plan from this command, its constraints, and the user's request, then execute the plan.

## Managed Observations

```bash
houmao-mgr --print-json agents single --agent-id "$AGENT_ID" state
houmao-mgr --print-json agents single --agent-id "$AGENT_ID" gateway status
houmao-mgr --print-json agents single --agent-id "$AGENT_ID" gateway tui state
```

Use `gateway tui history` or `gateway tui watch` when the caller specifically needs tracked history or observation over time. The verified-self lane uses the equivalent `agents self` commands. Pair-managed callers can read `GET /houmao/agents/{agent_ref}/managed-state` for identity and posture. Use `/state/detail` for raw observation or `/gateway/tui/state` and `/gateway/tui/history` for the live gateway's tracker. A detached gateway leaves record-backed state available and can make gateway-owned tracker evidence unavailable.

## Verified Local Tmux

Use the selected live runtime's verified manifest `tmux.socket_path`, `tmux.session_name`, and `tmux.primary_pane_id`. A verified active registry record can supply `terminal.socket_path` and `terminal.current_session_name`. Use current managed detail or the manifest for the exact pane. For example, `worker` and pane `%0` can exist on two different servers. The selected runtime's recorded socket identifies which pair belongs to it.

Run these commands only inside an accessible execution-owner context with an absolute verified socket and exact live target. Confirm the manifest and current managed identity describe the same live runtime before using its recorded pane. Use a bounded capture for ordinary inspection:

```bash
env -u TMUX -u TMUX_PANE tmux -S "$TMUX_SOCKET" -N capture-pane -p -e -S -100 -t "$PANE_ID"
```

For an explicit interactive attach, use the matching socket-qualified handoff or the command below. The `=` requests an exact session name.

```bash
env -u TMUX -u TMUX_PANE tmux -S "$TMUX_SOCKET" -N attach-session -t "=$SESSION_NAME"
```

If the recorded socket or exact target cannot be verified or reached, report that the local pane is unavailable and give the managed evidence that is available.

## Guardrails

- DO NOT use the caller's ambient tmux server for a selected agent.
- DO NOT infer a live target from a stopped record's last session name or a similarly named session.
- DO NOT start a server or relaunch the agent to inspect the pane.
- DO NOT use a headless supervisor pane as the primary source for managed turn state.
