# Archive Processed Mail

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

Archive a message only after the corresponding mailbox action succeeds and any required reply has been sent successfully.

Use `POST /v1/mail/archive` when a live gateway facade is available:

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/archive" \
  -H 'content-type: application/json' \
  --data '{"schema_version":1,"message_refs":["<opaque message_ref>"]}'
```

When no live gateway facade is available, run the direct fallback command:

```bash
<chosen houmao-mgr launcher> agents self mail archive --message-ref <message_ref>
```

Do not treat detection, peeking, reading, or replying as an implicit archive operation. Reply marks the parent message answered; archive closes the processed inbox work.
