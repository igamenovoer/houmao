# Determine Current Mailbox Bindings

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

If the current prompt or recent mailbox context already provides the exact gateway base URL or current mailbox binding set for this turn, use that value directly and do not rerun discovery first.

Otherwise run the direct current-session resolver:

```bash
<chosen houmao-mgr launcher> agents self mail resolve-live
```

Use the structured JSON output from that command as the supported mailbox-discovery contract for this turn.

When the output includes a `gateway` object:

- use `gateway.base_url` as the exact endpoint prefix for shared `/v1/mail/*` operations,
- keep using the opaque `message_ref` and `thread_ref` values returned by mailbox surfaces,
- do not guess a localhost port from unrelated process state.

When `gateway` is `null`:

- use the `mailbox.transport` value to choose the matching transport page inside this skill,
- run the matching `agents self mail <verb>` fallback command for that turn instead of guessing a direct shared-gateway endpoint.

When the command yields no usable current live binding for the current session at all, treat that as a signal that the caller is not currently operating as one live Houmao-managed agent. For operator-origin delivery into a managed agent mailbox, switch to `commands/post.md` instead of guessing a gateway route.
