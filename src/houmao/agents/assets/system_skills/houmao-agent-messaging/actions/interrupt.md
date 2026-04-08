# Interrupt A Managed Agent

Use this action only when the user wants the transport-neutral interrupt path for one already-running managed agent.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the target selector from the current prompt first and recent chat context second when it was stated explicitly.
3. If the target selector is still missing, ask the user in Markdown before proceeding.
4. Use `agents interrupt` for the default CLI path.
5. If the caller is already using the pair-managed HTTP API, use the managed-agent interrupt request surface under `POST /houmao/agents/{agent_ref}/requests`.
6. Report the interrupt result returned by the selected managed-agent surface.

## Command Shape

Use:

```text
<chosen houmao-mgr launcher> agents interrupt --agent-name <name>
```

Authoritative selector alternatives:

- `--agent-id <id>`
- `--port <pair-port>`

## Guardrails

- Do not redirect ordinary interrupt work to `agents gateway interrupt` unless the user explicitly wants gateway queue semantics.
- Do not guess the target managed agent.
- Do not describe interrupt as a mailbox or lifecycle action.
- Do not claim that interrupt guarantees immediate provider termination; it is the supported managed-agent interrupt request path.
