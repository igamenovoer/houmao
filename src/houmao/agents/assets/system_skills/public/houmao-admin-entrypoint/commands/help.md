# Help

## Workflow

1. **Keep help read-only** and skip target discovery, sibling loading, and command execution.
2. **Explain the actor posture**: the assistant acts for a human operator and never defaults to managed self.
3. **Summarize the route table** and identify `$houmao-shared-routines`, `$houmao-agent-loop-pro`, and `$houmao-agent-loop-lite` as top-level sibling destinations.
4. **Explain activation**: semantically Houmao-related operator requests may select this entrypoint implicitly, while exact `$houmao-*` handles select the named installed root.
5. **Show invocation forms** and recommend explicit `$houmao-admin-welcome ...` invocation for guided orientation without invoking it.

If the help request does not map cleanly to these steps, use the native planning tool to build a bounded read-only response from the entrypoint actor, route, target, and sibling contracts, then answer without execution.

Explain that target-sensitive work requires an explicit or unambiguously recovered target. Shared child names are route arguments, not independent `$skill` invocations.
