# Discover Managed-Agent Messaging Capability

Use this action when you need to identify the correct managed agent first or discover whether current gateway and mailbox handoff surfaces are available.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the target selector from the current prompt first and recent chat context second when it was stated explicitly.
3. If the target selector is still missing, ask the user in Markdown before proceeding.
4. If the request is generic read-only inspection rather than messaging preparation, hand it off to `houmao-agent-inspect`.
5. Run `agents state` first to confirm the managed-agent identity and current operational summary.
6. If the current task may need ordinary prompting, live gateway control, or any other gateway-preferred prompt routing decision, run `agents gateway status` next.
7. If the current task may need mailbox work or an exact live gateway base URL, run `agents mail resolve-live` next.
8. When the caller is already operating through the pair-managed HTTP API instead of the CLI, use the managed-agent routes summarized in `references/managed-agent-http.md`.
9. Report the target identity plus only the capability facts that matter for the next action: gateway availability, mailbox availability, exact `gateway.base_url` when present, and whether prompt or outgoing mailbox work should prefer a gateway-backed surface.

## Command Shapes

Use:

```text
<chosen houmao-mgr launcher> agents state --agent-name <name>
<chosen houmao-mgr launcher> agents gateway status --agent-name <name>
<chosen houmao-mgr launcher> agents mail resolve-live --agent-name <name>
```

Authoritative selector alternatives:

- `--agent-id <id>`
- `--port <pair-port>` for `agents state` and `agents mail resolve-live`
- `--pair-port <pair-port>` for `agents gateway status`

Managed-agent HTTP discovery surfaces:

- `GET /houmao/agents/{agent_ref}`
- `GET /houmao/agents/{agent_ref}/gateway`
- `GET /houmao/agents/{agent_ref}/mail/resolve-live`

## Guardrails

- Do not guess the target managed agent when the selector is missing or ambiguous.
- Do not keep generic liveness, log, artifact, or tmux inspection on this discovery action once it is clear the request is not about a messaging follow-up.
- Do not scrape tmux state directly when the managed-agent discovery surfaces already exist.
- Do not assume a gateway is attached just because the agent is currently running.
- Do not assume mailbox capability from the provider, role, or specialist name alone.
- Do not keep using stale capability assumptions across turns when the task depends on current live gateway or mailbox state.
