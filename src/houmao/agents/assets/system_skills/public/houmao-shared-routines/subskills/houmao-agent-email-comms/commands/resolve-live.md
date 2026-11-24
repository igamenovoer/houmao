# Determine Current Mailbox Bindings

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

Reuse the current sender binding when the validated actor context supplies it. For a gateway-specific action, reuse the exact live gateway base URL from that context when available.

Otherwise run the direct current-session resolver:

```bash
<chosen houmao-mgr launcher> agents self mail resolve-live
```

Use the structured JSON output to select `mailboxes.offline` or `mailboxes.online` and pin that slot's `binding.binding_id`. Use `agents self mail <verb>` for ordinary work on the selected binding.

For gateway-specific actions, use the verified `gateway.base_url` when the output includes a `gateway` object. Keep `message_ref` and `thread_ref` values opaque and scoped to their mailbox.

If the selected slot is absent or unavailable, report its mail configuration or connectivity error. Preserve the validated actor frame. Do not become the operator, select the other channel, or scrape credentials as a recovery step. Both absent slots are a valid mail-disabled agent state.
