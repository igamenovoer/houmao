# Reply To One Message

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

Reply using the opaque message reference and the current channel and binding.

```bash
houmao-mgr agents self mail reply --channel "$MAIL_CHANNEL" --expected-binding-id "$BINDING_ID" \
  --message-ref "$MESSAGE_REF" --body-content "$BODY"
```

Report the first receipt's status and top-level `message_ref`. The receipt's `parent_message_ref` identifies the message you replied to. Set `REPLY_REF` from the verified receipt's `message_ref` when you need the new reply's details.

```bash
houmao-mgr --print-json agents self mail peek --channel "$MAIL_CHANNEL" \
  --expected-binding-id "$BINDING_ID" --message-ref "$REPLY_REF"
```

Choose JSON on the first reply or on `peek`. If the outcome remains uncertain, check `mail list --box sent` on the replying agent's original binding. Use the parent's thread as a correlation hint. If the sent-box evidence is inconclusive, report the reply outcome as unresolved. An answered parent alone cannot confirm this particular reply.

A gateway reply requires `mail.reply` on the selected binding. A request carrying owner-file attachments also requires `mail.attachment.owner_file` on that binding. Keep transport-local threading identifiers opaque. [Write Permissions](../references/endpoint-contract.md#write-permissions)

Interpret `transport_evidence` on verified writes as offline deposit or provider submission. Confirm uncertainty on the original binding. The receipt does not disclose recipient Inbox placement.
