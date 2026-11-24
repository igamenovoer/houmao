# Reconcile a File Publication Attempt

## Workflow

1. Recover the original operation ID, selected mount, target binding, and candidate from the recorded attempt. Select a caller with current `files.read`.
2. Use the currently verified endpoint for that target and call `status` with the original operation ID.
3. Report the strongest retained evidence using [Push Receipts](../references/receipts.md), including any native state that remains unknown.

Use the native planning tool for a wider investigation, keeping the outstanding attempt read-only and keyed to the original ID.

## Command Example

The Bash `files` prefix must have a verified endpoint and a caller with current read authority. After a gateway restart, establish trusted coordinates for the current listener before querying the same target attempt.

```bash
"${files[@]}" --mount "$MOUNT_ID" status "$OPERATION_ID"
```

A lost response can leave a completed or outstanding attempt. A pending or unknown status can be checked again by the original ID. If the current target or caller cannot read the receipt, report the missing evidence and hand it to the authorized owner.

## Guardrails

- DO NOT submit a new push to learn how an earlier one ended.
- DO NOT infer a terminal result from an unreachable or changed listener.
- DO NOT treat partial activation or an unknown readiness field as a ready agent.
