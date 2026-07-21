# Check Mailbox Status

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

Use mailbox status when you need to confirm mailbox identity, current transport, or live gateway availability before taking action.

When a live shared gateway mailbox facade is already available, use:

```bash
curl -sS "$GATEWAY_BASE_URL/v1/mail/status"
```

When no live gateway facade is available for this turn, run the direct fallback command:

```bash
<chosen houmao-mgr launcher> agents self mail status
```

Treat the returned mailbox identity and transport fields as the current supported state for this turn.
