# Archive Processed Mail

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

Archive a message only after the corresponding mailbox action succeeds and any required reply has been sent successfully.

Run the scoped command after the processing and any required reply succeed.

```bash
houmao-mgr agents self mail archive --channel "$MAIL_CHANNEL" --expected-binding-id "$BINDING_ID" --message-ref "$MESSAGE_REF"
```

Reply marks the parent message answered. Archive closes the processed inbox work.
