# Inspect The Live Screen Or TUI Posture

Use this action when the user wants to inspect what is currently visible for a managed agent, especially for TUI-backed sessions.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the target selector from the current prompt first and recent chat context second when it was stated explicitly.
3. If the target is still missing, ask the user in Markdown before proceeding.
4. Run `agents state` or `GET /houmao/agents/{agent_ref}/state` first to confirm the transport and whether the target is TUI-backed or headless.
5. For TUI-backed agents, use `GET /houmao/agents/{agent_ref}/state/detail`, `agents gateway status`, or the matching gateway route as needed to recover the exact tmux session name or pane target.
6. Once the exact tmux session or pane target is identified, inspect the live pane with local tmux capture before checking gateway TUI tracker state or history.
7. Use `agents gateway tui state|history|watch` or the matching managed-agent gateway TUI routes when the task needs gateway-owned tracked-screen state, history, or watch behavior after the live tmux pane has been inspected.
8. For headless agents, keep this action narrow: use detailed state to confirm there is no TUI surface and then route durable execution evidence to `actions/logs.md`.
9. Use direct local tmux attach only when the caller explicitly wants an attached live pane.

## Command Shapes

Managed-agent and gateway identification surfaces:

```text
<chosen houmao-mgr launcher> agents state --agent-name <name>
<chosen houmao-mgr launcher> agents gateway status --agent-name <name>
```

Primary tmux screen inspection once the session name or pane target is identified:

```text
tmux capture-pane -p -e -S - <tmux-target>
```

Gateway tracker surfaces for raw tracked state, history, or watch behavior:

```text
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

Local attach for explicit live-pane requests:

```text
env -u TMUX tmux attach-session -t <tmux-session-name>
```

Use the tmux lane after the managed-agent and gateway surfaces have already identified the exact tmux target or session.

## Guardrails

- Do not present raw tmux attach or pane capture as the default first inspection step before the exact tmux target or session is identified.
- Do not use `agents gateway tui ...` as the first screen-inspection source after the exact tmux target or session is identified unless the task specifically asks for gateway-owned tracked state or history.
- Do not treat gateway TUI tracker state as the canonical contract for headless agents.
- Do not guess the tmux target from naming conventions alone; recover it from managed-agent identity and detail first.
