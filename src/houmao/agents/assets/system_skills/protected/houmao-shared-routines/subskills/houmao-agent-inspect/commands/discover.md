# Discover Managed-Agent Inspection Targets

Use this action when you first need to identify the correct managed agent or confirm the current liveness and capability posture before deeper inspection.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the target selector from the current prompt first and recent chat context second when it was stated explicitly.
3. If the target is still missing or ambiguous, use `agents global list` first or ask the user for the missing selector.
4. Run `agents single --agent-name <name> state`, `agents single --agent-id <id> state`, or `GET /houmao/agents/{agent_ref}/state` first to recover summary identity, liveness, `manifest_path`, and `session_root`.
5. If the request needs transport-specific detail, run `GET /houmao/agents/{agent_ref}/state/detail` next.
6. If the request may need current live gateway posture, run `agents single --agent-name <name> gateway status` or `GET /houmao/agents/{agent_ref}/gateway`.
7. Report only the facts needed for the next step: tracked identity, transport, runtime posture, gateway presence, and the stable artifact pointers already exposed by the response.

## Command Shapes

Use:

```text
<chosen houmao-mgr launcher> agents global list
<chosen houmao-mgr launcher> agents single --agent-name <name> state
<chosen houmao-mgr launcher> agents single --agent-id <id> state
<chosen houmao-mgr launcher> agents single --agent-name <name> gateway status
```

Authoritative selector alternatives:

- `--port <pair-port>` for `agents single ... state`
- `--pair-port <pair-port>` for `agents single ... gateway status`

Managed-agent HTTP discovery surfaces:

- `GET /houmao/agents`
- `GET /houmao/agents/{agent_ref}/state`
- `GET /houmao/agents/{agent_ref}/state/detail`
- `GET /houmao/agents/{agent_ref}/gateway`

## Guardrails

- Do not guess the target managed agent when the selector is missing or ambiguous.
- Do not skip summary state and jump straight to tmux or runtime files before the exact target and session identity are known.
- Do not treat `/history` as a substitute for the transport-specific rich detail surface.
- Do not keep using stale gateway or mailbox assumptions across turns when current live state matters.
