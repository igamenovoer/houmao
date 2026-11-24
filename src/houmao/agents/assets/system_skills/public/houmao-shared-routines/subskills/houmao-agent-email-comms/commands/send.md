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

Report `status` and the top-level `message_ref` from this receipt. `status: verified` and `authoritative: true` confirm an acknowledged write. Choose `--print-json` on the first send if you need structured output. Use read-only `peek` for details on the sender's original channel and binding.

```bash
houmao-mgr --print-json agents self mail peek --channel "$MAIL_CHANNEL" \
  --expected-binding-id "$BINDING_ID" --message-ref "$RECEIPT_REF"
```

If the outcome is uncertain or the result only confirms submission, keep the receipt's request ID when present. Check `mail list --box sent` on the sender's original channel and binding when authorized. Report the outcome as unresolved if the read is unavailable or inconclusive.

The gateway requires verified admin proof for owner-file attachments on this private route.
