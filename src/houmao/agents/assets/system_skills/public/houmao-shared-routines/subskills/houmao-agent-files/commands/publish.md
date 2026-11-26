# Publish a Saved Candidate (`publish`)

## Workflow

1. **Verify target, mount, immutable candidate commit, and `--expected-base`**, and select a mode-appropriate caller with `files.push` on `files:<mount-id>` (such as `builtin:agent-maintainer`, `skill-publisher`, `skill-maintainer`, `managed-self`, or `--unsigned` on an initialized `open` gateway; see [Mount Scope](../references/mount-scope.md)).
2. **Allocate and retain a fresh `--operation-id`** for this attempt and submit `push` once against `--expected-base` (using self-only `--when-idle` when publishing onto your own active runtime turn).
3. **Interpret the receipt** via [Push Receipts](../references/receipts.md), reporting publisher attribution, publication, native activation, settlement, and readiness separately.
4. **Reconcile or recover cleanly**: on an uncertain transport outcome, run [Reconcile](reconcile.md) (`status "$OPERATION_ID"`) with the **same** `--operation-id` without replaying; on a base conflict, inspect the newer revision and open a fresh draft; on a confirmed busy refusal, preserve the saved candidate and follow the stderr signer/retry hint once idle (or use self-only `--when-idle`).

Use the native planning tool for multi-stage review, approval, and publication workflows while preserving this attempt boundary.

## Mode-Aware Command Examples

```bash
# Keyed gateway: enrolled publisher key (--signer), --source-agent-id, or --self-signer
houmao-mgr --print-json agents single --agent-id "$TARGET_AGENT_ID" files \
  --signer "$PUBLISHER_KEY" --mount "$MOUNT_ID" \
  push "$CANDIDATE_COMMIT" --expected-base "$BASE_COMMIT" --operation-id "$OPERATION_ID"

# Open-roster gateway (admin_mode: open): explicit --unsigned admission
houmao-mgr --print-json agents single --agent-id "$TARGET_AGENT_ID" files \
  --unsigned --mount "$MOUNT_ID" \
  push "$CANDIDATE_COMMIT" --expected-base "$BASE_COMMIT" --operation-id "$OPERATION_ID"

# Self-only busy-turn recovery: queue exact candidate while your own turn is active
houmao-mgr --print-json agents self files --mount "$MOUNT_ID" \
  push "$CANDIDATE_COMMIT" --expected-base "$BASE_COMMIT" --operation-id "$OPERATION_ID" --when-idle
```

Inspect queued `--when-idle` or settled receipts via `houmao-mgr --print-json agents self files --mount "$MOUNT_ID" status "$OPERATION_ID"`. A caller with `files.push` (for example `skill-publisher`) can publish a candidate authored by a separate `skill-editor`; history preserves both author and publisher attribution.

## Guardrails

- DO NOT push a mutable draft ID, guess `--expected-base`, omit `--operation-id`, or use `--when-idle` outside `agents self files`.
- DO NOT claim native runtime readiness from exit code `0` or publication commit alone.
- DO NOT replay an uncertain `push` with a new `--operation-id` or run native `refresh` to force settlement.
