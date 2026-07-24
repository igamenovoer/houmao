# Decide What To Read

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

Use `POST /v1/mail/peek` to inspect one selected message without marking it read. Use `POST /v1/mail/read` only when you intentionally want to inspect the message and mark it read.

Use `POST /v1/mail/list` to inspect the current inbox queue, then choose which `message_ref` to act on next.

Treat `message_ref` and `thread_ref` as opaque identifiers.

Peek example:

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/peek" \
  -H 'content-type: application/json' \
  --data '{"schema_version":1,"message_ref":"<opaque message_ref>"}'
```

Read example:

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/read" \
  -H 'content-type: application/json' \
  --data '{"schema_version":1,"message_ref":"<opaque message_ref>"}'
```

When multiple open messages exist:

- use the metadata returned by `list`,
- choose the message or messages to inspect,
- re-list if the inbox snapshot may have changed before taking more actions.

When no live gateway facade is available, run the direct fallback command for the selected message:

```bash
<chosen houmao-mgr launcher> agents self mail peek --message-ref <message_ref>
<chosen houmao-mgr launcher> agents self mail read --message-ref <message_ref>
```
