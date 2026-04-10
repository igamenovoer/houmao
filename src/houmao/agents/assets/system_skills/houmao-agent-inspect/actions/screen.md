# Inspect The Live Screen Or TUI Posture

Use this action when the user wants to inspect what is currently visible for a managed agent, especially for TUI-backed sessions.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the target selector from the current prompt first and recent chat context second when it was stated explicitly.
3. If the target is still missing, ask the user in Markdown before proceeding.
4. Run `agents state` or `GET /houmao/agents/{agent_ref}/state` first to confirm the transport and whether the target is TUI-backed or headless.
5. For TUI-backed agents, prefer `GET /houmao/agents/{agent_ref}/state/detail` next when the user wants curated transport detail rather than the raw tracker payload.
6. For TUI-backed agents with a healthy live gateway, prefer `agents gateway tui state|history|watch` or the matching managed-agent gateway TUI routes for raw tracked-screen inspection.
7. For headless agents, keep this action narrow: use detailed state to confirm there is no TUI surface and then route durable execution evidence to `actions/logs.md`.
8. Use direct local tmux capture or attach only when the caller explicitly wants the live local pane or the supported managed-agent and gateway inspection surfaces are insufficient.

## Command Shapes

Preferred managed-agent and gateway surfaces:

```text
<chosen houmao-mgr launcher> agents state --agent-name <name>
<chosen houmao-mgr launcher> agents gateway status --agent-name <name>
<chosen houmao-mgr launcher> agents gateway tui state --agent-name <name>
<chosen houmao-mgr launcher> agents gateway tui history --agent-name <name>
<chosen houmao-mgr launcher> agents gateway tui watch --agent-name <name>
```

Managed-agent HTTP routes:

- `GET /houmao/agents/{agent_ref}/state`
- `GET /houmao/agents/{agent_ref}/state/detail`
- `GET /houmao/agents/{agent_ref}/gateway`
- `GET /houmao/agents/{agent_ref}/gateway/tui/state`
- `GET /houmao/agents/{agent_ref}/gateway/tui/history`

Local last-resort tmux peek:

```text
tmux capture-pane -p -e -S - <tmux-target>
env -u TMUX tmux attach-session -t <tmux-session-name>
```

Use the tmux lane only after the managed-agent and gateway surfaces have already identified the exact tmux target or session.

## Guardrails

- Do not present raw tmux attach or pane capture as the default first inspection step for a TUI-backed agent.
- Do not use `agents gateway tui ...` unless the task genuinely needs raw gateway-owned tracked state or history.
- Do not treat gateway TUI tracker state as the canonical contract for headless agents.
- Do not guess the tmux target from naming conventions alone; recover it from managed-agent identity and detail first.
