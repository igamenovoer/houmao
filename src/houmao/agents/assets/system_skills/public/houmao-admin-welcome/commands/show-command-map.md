# Show Command Map

## Workflow

1. **Keep the command map read-only** and do not execute any shown invocation.
2. **List welcome commands** under `$houmao-admin-welcome <command>`.
3. **List execution routes** under `$houmao-admin-entrypoint <route> <operation>` and name their public sibling destinations.
4. **Distinguish public roots from parent-scoped children** and show pro and lite as top-level manual skills.

If the request does not map cleanly to these steps, use the native planning tool to build a bounded read-only command map from the current public inventory and route tables, then return it without execution.

Show only public invocations. Explain that route segments such as `agent-inspect`, `credential-mgr`, and `mailbox-mgr` are children owned by the public `$houmao-shared-routines` sibling, not independently installed skills.
