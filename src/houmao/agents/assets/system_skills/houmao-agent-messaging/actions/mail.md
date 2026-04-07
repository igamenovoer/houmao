# Use Managed-Agent Mail Follow-Up

Use this action only when the target has mailbox capability and the work should be expressed as mailbox follow-up instead of a normal prompt turn or raw gateway control.

## Workflow

1. Use the launcher resolved from the top-level skill.
2. Recover the target selector and mailbox intent from the current prompt first and recent chat context second when they were stated explicitly.
3. If the target selector or mailbox intent is still missing, ask the user in Markdown before proceeding.
4. Use `agents mail resolve-live` first when the task needs current mailbox bindings, mailbox capability confirmation, or an exact live `gateway.base_url`, and always do that before outgoing mailbox work when gateway preference matters.
5. When `resolve-live` returns a live `gateway.base_url`, prefer the live gateway mailbox facade for shared mailbox work, especially outgoing mail operations, and hand off to `houmao-email-via-agent-gateway`.
6. Use the managed-agent mailbox commands or `/houmao/agents/{agent_ref}/mail/*` routes only when no live gateway mailbox facade is available or the task explicitly needs the transport-neutral managed-agent seam:
   - `status`
   - `check`
   - `send`
   - `reply`
   - `mark-read`
7. When the mailbox task becomes a notifier-driven round with a live gateway mailbox facade, hand off to `houmao-process-emails-via-gateway`.
8. When the mailbox task needs filesystem-specific or Stalwart-specific behavior, hand off to `houmao-email-via-filesystem` or `houmao-email-via-stalwart`.
9. Report the mailbox result and call out whether it used the live gateway mailbox facade or a fallback managed-agent surface.

## Command Shapes

Resolve live bindings:

```text
<resolved houmao-mgr launcher> agents mail resolve-live --agent-name <name>
```

Common mailbox follow-up:

```text
<resolved houmao-mgr launcher> agents mail status --agent-name <name>
<resolved houmao-mgr launcher> agents mail check --agent-name <name>
<resolved houmao-mgr launcher> agents mail send --agent-name <name> ...
<resolved houmao-mgr launcher> agents mail reply --agent-name <name> ...
<resolved houmao-mgr launcher> agents mail mark-read --agent-name <name> --message-ref <message_ref>
```

Managed-agent HTTP mailbox surfaces:

- `GET /houmao/agents/{agent_ref}/mail/resolve-live`
- `GET /houmao/agents/{agent_ref}/mail/status`
- `POST /houmao/agents/{agent_ref}/mail/check`
- `POST /houmao/agents/{agent_ref}/mail/send`
- `POST /houmao/agents/{agent_ref}/mail/reply`
- `POST /houmao/agents/{agent_ref}/mail/state`

When `resolve-live` returns a live `gateway.base_url`, prefer the shared gateway mailbox skill instead of restating the lower-level `/v1/mail/*` contract here.

## Guardrails

- Do not guess mailbox capability, mailbox addresses, or message references.
- Do not restate filesystem layout, Stalwart credential handling, or the lower-level `/v1/mail/*` contract here.
- Do not mark a message read before the corresponding send, reply, or processing action succeeds.
- Do not turn mailbox follow-up into a raw `send-keys` or ordinary prompt workflow.
- Do not skip `agents mail resolve-live` when the task depends on whether a live gateway mailbox facade exists.
- Do not keep outgoing mailbox work on fallback managed-agent mail surfaces once `resolve-live` already shows a live gateway mailbox facade, unless the task explicitly needs a fallback or transport-local behavior.
- Do not guess a direct gateway base URL for mailbox work.
