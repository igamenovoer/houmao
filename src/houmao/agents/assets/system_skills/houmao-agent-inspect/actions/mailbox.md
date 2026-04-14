# Inspect Mailbox Posture

Use this action when the inspection task is about mailbox identity, unread posture, current live mailbox capability, or late local mailbox-binding posture.

## Workflow

1. Use the `houmao-mgr` launcher already chosen by the top-level skill.
2. Recover the target selector from the current prompt first and recent chat context second when it was stated explicitly.
3. If the target is still missing, ask the user in Markdown before proceeding.
4. Use `agents mail resolve-live` first when the task needs current mailbox identity, current live gateway mailbox capability, or the exact live `gateway.base_url`.
5. Use `agents mail status` when the task is to inspect current mailbox posture for one managed agent.
6. Use `agents mail list` when the task is to inspect current unread or recent message state without mutating it.
7. Use `agents mailbox status` only when the task is to inspect late filesystem mailbox-binding posture for one local managed agent.
8. If the task turns into mailbox-root administration, mailbox registrations, or projected mailbox structure, hand it off to `houmao-mailbox-mgr` instead of duplicating that guidance here.

## Command Shapes

Use:

```text
<chosen houmao-mgr launcher> agents mail resolve-live --agent-name <name>
<chosen houmao-mgr launcher> agents mail status --agent-name <name>
<chosen houmao-mgr launcher> agents mail list --agent-name <name> --read-state unread
<chosen houmao-mgr launcher> agents mailbox status --agent-name <name>
```

Managed-agent HTTP mailbox inspection routes:

- `GET /houmao/agents/{agent_ref}/mail/resolve-live`
- `GET /houmao/agents/{agent_ref}/mail/status`
- `POST /houmao/agents/{agent_ref}/mail/list`

## Guardrails

- Do not skip `agents mail resolve-live` when the request depends on current live mailbox or gateway-backed mailbox capability.
- Do not treat structural mailbox-root inspection as the same thing as actor-scoped unread or mailbox-identity inspection.
- Do not route mailbox send, reply, post, mark, move, or archive through this inspection action.
- Do not use `agents mailbox status` as a substitute for ordinary mailbox follow-up state.
