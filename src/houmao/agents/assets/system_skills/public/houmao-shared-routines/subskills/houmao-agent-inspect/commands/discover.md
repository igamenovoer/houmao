# Discover Managed-Agent Inspection Targets

Use this action when you first need to identify the correct managed agent or confirm the current liveness and capability posture before deeper inspection.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the target selector from the current prompt first and recent chat context second when it was stated explicitly.
3. If the target is still missing or ambiguous, use `agents global list` first or ask the user for the missing selector.
4. Use scoped CLI `state` or `GET /houmao/agents/{agent_ref}/managed-state` first. Read identity, liveness, and any manifest or session-root pointers returned for the selected agent.
5. If the request needs transport-specific detail, use `/managed-state/detail` or the corresponding raw `/state/detail` observation for the selected agent.
6. If the request may need current live gateway posture, run `agents single --agent-name <name> gateway status` or `GET /houmao/agents/{agent_ref}/gateway`.
7. Report only the facts needed for the next step: tracked identity, transport, runtime posture, gateway presence, and the stable artifact pointers already exposed by the response.

If the request does not map cleanly to this workflow, use the native planning tool to build a step-by-step plan from the owning skill, this procedure, its constraints, available references, and the user request, then execute the plan.

## Command Shapes

Use:

```text
<chosen houmao-mgr launcher> agents global list
<chosen houmao-mgr launcher> agents single --agent-name <name> state
<chosen houmao-mgr launcher> agents single --agent-id <id> state
<chosen houmao-mgr launcher> agents single --agent-name <name> gateway status
```

Select the agent with `--agent-id` or `--agent-name` on `agents single`. When an explicit passive server port is needed, pass `--port` to `state` or `--pair-port` to `gateway status` after the selected agent. For genuine managed self, use the equivalent `agents self` command.

Managed-agent HTTP discovery surfaces:

- `GET /houmao/agents`
- `GET /houmao/agents/{agent_ref}/managed-state`
- `GET /houmao/agents/{agent_ref}/managed-state/detail`
- `GET /houmao/agents/{agent_ref}/state`
- `GET /houmao/agents/{agent_ref}/state/detail`
- `GET /houmao/agents/{agent_ref}/gateway`

## Guardrails

- DO NOT guess the target managed agent when the selector is missing or ambiguous.
- DO NOT skip summary state and jump straight to tmux or runtime files before the exact target and session identity are known.
- DO NOT treat `/history` as a substitute for the transport-specific rich detail surface.
- DO NOT keep using stale gateway or mailbox assumptions across turns when current live state matters.
