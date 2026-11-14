# Leave Offline Mail Without Relaunch

## Workflow

1. Preserve the actor frame and selected managed-agent target.
2. Confirm explicit release intent and the chosen retention policy.
3. Run offline leave below, preserving online mail and the body.
4. Report confirmed release and any local publication reconciliation.

If the request does not map cleanly to this workflow, use the native planning tool to build a step-by-step plan from the owning skill, this procedure, its constraints, available references, and the user request, then execute the plan.

## Procedure

Select an explicit managed agent under the admin frame, or verified self under the agent frame. Explicit leave releases offline membership and preserves online mail and internal agent identity.

```bash
<chosen houmao-mgr launcher> agents single --agent-id <agent-id> mailbox offline leave [--mode deactivate|purge]
<chosen houmao-mgr launcher> agents self mailbox offline leave
```

Use the default `deactivate` retention policy unless the user selected stronger local removal. A remote member releases its own registration through the registry API. Retained history stays owned by the old registration; a later address owner receives a fresh registration and cannot inherit private views or old references.

Stopping the body, losing a gateway, or attaching online mail does not release offline membership. Do not reinterpret a mailbox-root cleanup request as agent leave or vice versa. Report the confirmed registration release and any local publication reconciliation needed.
