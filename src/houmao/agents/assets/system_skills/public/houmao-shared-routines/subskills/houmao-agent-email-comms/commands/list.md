# List Mail Through The Gateway

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

Use `POST /v1/mail/list` to inspect the current mailbox state through the live shared gateway facade.

Typical unread list:

```bash
curl -sS -X POST "$GATEWAY_BASE_URL/v1/mail/list" \
  -H 'content-type: application/json' \
  --data '{"schema_version":1,"box":"inbox","read_state":"unread","answered_state":"any","archived":false,"limit":10}'
```

When no live gateway facade is available, run the direct fallback command:

```bash
<chosen houmao-mgr launcher> agents self mail list --box inbox
```

Use the response to inspect current unread headers and any returned message detail for the turn.
