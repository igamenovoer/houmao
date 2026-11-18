# Post An Operator-Origin Note

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

Use this action when the caller is acting as operator and needs to deliver one operator-origin note into a managed agent mailbox.

Select the agent and current binding explicitly.

```bash
houmao-mgr agents single --agent-id "$AGENT_ID" mail post --channel "$MAIL_CHANNEL" \
  --expected-binding-id "$BINDING_ID" --subject "$SUBJECT" --body-content "$BODY"
```

With a live gateway, post follows the admin rule. Configure an explicit owner-side admin signer for a key-required gateway. A detached gateway uses the separately authorized manager path.

This action is filesystem-only in v1. It delivers from the reserved sender `HOUMAO-operator@houmao.localhost`, refuses Stalwart-backed execution, and does not allow live TUI submission fallback.

By default, operator-origin posts use `reply_policy=operator_mailbox`, so replies to that message route back to the reserved operator mailbox. Use `reply_policy=none` only when the caller explicitly wants a one-way operator note.
