# Send A New Message

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

Use this action for ordinary managed-agent outbound shared mailbox messages.

If the caller is acting as operator and needs to leave an operator-origin note in a managed agent mailbox, use `commands/post.md` instead of ordinary `send`.

Use `POST /v1/mail/send` to create one new outbound shared mailbox message.

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/send" \
  -H 'content-type: application/json' \
  --data '{"schema_version":1,"to":["recipient@houmao.localhost"],"subject":"...","body_content":"...","attachments":[]}'
```

Use the exact `gateway.base_url` resolved for this turn.

When no live gateway facade is available, run the direct fallback command:

```bash
<chosen houmao-mgr launcher> agents self mail send --to <recipient> --subject <subject> --body-content <body>
```
