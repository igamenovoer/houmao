# Discover Managed-Agent Messaging Capability

Use this action when you need to identify the correct managed agent first or discover whether current gateway and mailbox handoff surfaces are available.

## Workflow

1. Use the launcher resolved from the top-level skill.
2. Recover the target selector from the current prompt first and recent chat context second when it was stated explicitly.
3. If the target selector is still missing, ask the user in Markdown before proceeding.
4. Run `agents state` first to confirm the managed-agent identity and current operational summary.
5. If the current task may need ordinary prompting, live gateway control, or any other gateway-preferred prompt routing decision, run `agents gateway status` next.
6. If the current task may need mailbox work or an exact live gateway base URL, run `agents mail resolve-live` next.
7. When the caller is already operating through the pair-managed HTTP API instead of the CLI, use the managed-agent routes summarized in `references/managed-agent-http.md`.
8. Report the target identity plus only the capability facts that matter for the next action: gateway availability, mailbox availability, exact `gateway.base_url` when present, and whether prompt or outgoing mailbox work should prefer a gateway-backed surface.

## Command Shapes

Use:

```text
<resolved houmao-mgr launcher> agents state --agent-name <name>
<resolved houmao-mgr launcher> agents gateway status --agent-name <name>
<resolved houmao-mgr launcher> agents mail resolve-live --agent-name <name>
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
- Do not scrape tmux state directly when the managed-agent discovery surfaces already exist.
- Do not assume a gateway is attached just because the agent is currently running.
- Do not assume mailbox capability from the provider, role, or specialist name alone.
- Do not keep using stale capability assumptions across turns when the task depends on current live gateway or mailbox state.
