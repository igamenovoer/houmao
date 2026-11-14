# Decide What To Read

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

Use `POST /v1/mail/{channel}/peek` to inspect one selected message without marking it read. Use `POST /v1/mail/{channel}/read` only when you intentionally want to inspect the message and mark it read.

Use `POST /v1/mail/{channel}/list` to inspect the current inbox queue, then choose which `message_ref` to act on next.

Treat `message_ref` and `thread_ref` as opaque identifiers.

Check `content_complete`, `content_limit_bytes`, and `content_limit_reason` on selected content. A false completeness flag or explicit provider limit means the returned text is partial. Use an authorized retrieval path only when the response supplies one; otherwise report the missing content instead of inventing a blob URL or claiming full inspection.

Peek example:

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/$MAIL_CHANNEL/peek" \
  -H 'content-type: application/json' \
  --data '{"schema_version":3,"expected_binding_id":"<selected binding_id>","message_ref":"<opaque message_ref>"}'
```

Read example:

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/$MAIL_CHANNEL/read" \
  -H 'content-type: application/json' \
  --data '{"schema_version":3,"expected_binding_id":"<selected binding_id>","message_ref":"<opaque message_ref>"}'
```

When multiple open messages exist:

- use the metadata returned by `list`,
- choose the message or messages to inspect,
- stop the current page chain if its cursor becomes stale, and preserve the same channel/binding for any separately requested fresh triage.

When no live gateway facade is available, run the direct fallback command for the selected message:

```bash
<chosen houmao-mgr launcher> agents self mail peek --channel <channel> --expected-binding-id <binding_id> --message-ref <message_ref>
<chosen houmao-mgr launcher> agents self mail read --channel <channel> --expected-binding-id <binding_id> --message-ref <message_ref>
```
