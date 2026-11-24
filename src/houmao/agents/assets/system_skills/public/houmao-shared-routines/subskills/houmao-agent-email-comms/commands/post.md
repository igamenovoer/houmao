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

Report the first receipt's status and top-level `message_ref`. The receipt's `address` and `binding_id` identify the selected recipient mailbox. Its `sender_address` identifies the operator. Use the recipient's original scope to inspect the posted message, even if the recipient has since archived it.

```bash
houmao-mgr --print-json agents single --agent-id "$AGENT_ID" mail peek \
  --channel "$MAIL_CHANNEL" --expected-binding-id "$BINDING_ID" --message-ref "$POST_REF"
```

If the post outcome is uncertain, inspect the same target binding's inbox and archive where authorized. Report the outcome as unresolved if the evidence is inconclusive.

A gateway post requires `mail.post` on the selected binding. A request carrying owner-file attachments also requires `mail.attachment.owner_file` on that binding. Use the configured owner-side administrator signer for the ordinary scoped CLI on a keyed gateway. A detached gateway uses the separately authorized manager path. [Write Permissions](../references/endpoint-contract.md#write-permissions)

This action is filesystem-only in v1. It delivers from the reserved sender `HOUMAO-operator@houmao.localhost`, refuses Stalwart-backed execution, and does not allow live TUI submission fallback.

By default, operator-origin posts use `reply_policy=operator_mailbox`, so replies to that message route back to the reserved operator mailbox. Use `reply_policy=none` only when the caller explicitly wants a one-way operator note.
