# Send A New Message

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

Use this action for ordinary managed-agent outbound shared mailbox messages.

If the caller is acting as operator and needs to leave an operator-origin note in a managed agent mailbox, use `commands/post.md` instead of ordinary `send`.

Use the known recipient address for the explicit channel. If the request names a peer and omits its address, read `houmao-mgr agents single --agent-name <name> mail resolve-live`. Published contact is sufficient for addressing the message. Delivery checks registration independently of recipient readiness and gateway status.

Run the scoped command with the sender's verified binding ID for that channel.

```bash
houmao-mgr agents self mail send --channel "$MAIL_CHANNEL" --expected-binding-id "$BINDING_ID" \
  --to "$RECIPIENT" --subject "$SUBJECT" --body-content "$BODY"
```

The gateway requires verified admin proof for owner-file attachments on this private route.
