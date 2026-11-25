# Publish a Saved Candidate

## Workflow

1. Verify the selected target, mount, immutable candidate, and recorded base. Select a caller with current `files.push` on the resource.
2. Allocate and retain a fresh operation ID for this intended attempt. Submit the exact candidate and expected base once.
3. Read the response using [Push Receipts](../references/receipts.md). Report the publisher and the evidence for publication, native activation, settlement, and readiness separately.
4. For an uncertain result, use [Reconcile](reconcile.md) with the same operation ID.

Use the native planning tool for a publication request with separate review, approval, and execution stages while preserving this attempt boundary.

## Command Example

This example selects the owner-local live gateway and an enrolled publisher. Keep the chosen operation ID with the attempted target, mount, candidate, and expected base.

```bash
publisher=(houmao-mgr --print-json agents single --agent-id "$TARGET_AGENT_ID" files
  --signer "$PUBLISHER_KEY" --mount "$MOUNT_ID")
"${publisher[@]}" push "$CANDIDATE_COMMIT" --expected-base "$BASE_COMMIT" \
  --operation-id "$OPERATION_ID"
```

Use the remote endpoint and signer choices from [Mount Scope](../references/mount-scope.md) when the publisher works from another account. A caller with `files.push` can publish another actor's candidate. The receipt attributes the publisher separately from the author recorded in history.

Within your own runtime, current managed-self proof can queue the exact candidate while your turn is active.

```bash
houmao-mgr --print-json agents self files --mount "$MOUNT_ID" push "$CANDIDATE_COMMIT" \
  --expected-base "$BASE_COMMIT" --operation-id "$OPERATION_ID" --when-idle
```

Use `agents self files --mount "$MOUNT_ID" status "$OPERATION_ID"` to read a queued or settled receipt.

If publication conflicts with a newer base, inspect the current revision and prepare a fresh draft for the intended changes. A confirmed busy result preserves the saved candidate. Use the stderr hint to select an explicit new attempt with that candidate, its recorded base, and a fresh operation ID. A verified managed-self caller can request `--when-idle` explicitly. Other callers can make the new attempt once the target is ready. Use the receipt outcome to determine whether an intent was queued.

## Guardrails

- DO NOT push a draft ID, a guessed base, or a candidate on a different mount.
- DO NOT claim readiness from the exit status or publication field alone.
- DO NOT resubmit an uncertain push or invoke native refresh to force a result.
