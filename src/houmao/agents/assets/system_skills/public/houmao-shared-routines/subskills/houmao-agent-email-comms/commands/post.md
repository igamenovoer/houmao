# Post An Operator-Origin Note

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

Use this action when the caller is acting as operator and needs to deliver one operator-origin note into a managed agent mailbox.

When the caller is outside the Houmao managed-agent runtime, or current discovery shows there is no usable live gateway for the current session, run the direct fallback command:

```bash
<chosen houmao-mgr launcher> agents single --agent-id <agent-id> mail post --subject <subject> --body-content <body>
```

When the exact target managed-agent `gateway.base_url` is already known for this turn, `POST /v1/mail/post` is also supported:

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/post" \
  -H 'content-type: application/json' \
  --data '{"schema_version":1,"subject":"...","body_content":"...","attachments":[]}'
```

Use the exact `gateway.base_url` resolved for the selected managed agent when taking the gateway route.

This action is filesystem-only in v1. It delivers from the reserved sender `HOUMAO-operator@houmao.localhost`, refuses Stalwart-backed execution, and does not allow live TUI submission fallback.

By default, operator-origin posts use `reply_policy=operator_mailbox`, so replies to that message route back to the reserved operator mailbox. Use `reply_policy=none` only when the caller explicitly wants a one-way operator note.
