## Context

`houmao-mgr mailbox clear-messages` currently clears all delivered message content in a resolved filesystem mailbox root while preserving registrations. The project wrapper exposes the same all-account reset under `houmao-mgr project mailbox clear-messages`.

The message inspection surface is already account-scoped through `houmao-mgr mailbox messages list|get --address <full-address>` and the project equivalent. The missing operation is a maintained account-scoped clear path. Directly deleting files is unsafe because delivered mail has shared canonical message files, per-account projection symlinks, shared SQLite catalog rows, and mailbox-local SQLite state.

The key constraint is that canonical messages are shared. Delivery creates a sender projection, recipient projections, and one canonical message document. Clearing one account must remove that account's visibility without deleting canonical history still visible to other accounts.

## Goals / Non-Goals

**Goals:**

- Add a maintained CLI path to clear messages for exactly one active mailbox address.
- Preserve all mailbox registrations, including the selected account registration.
- Preserve other accounts' projections and message visibility.
- Remove canonical message files and managed-copy attachments only when no remaining mailbox projection or message reference needs them.
- Reuse the existing cleanup payload model, dry-run behavior, and destructive confirmation pattern.
- Mirror generic mailbox behavior under the selected project overlay.
- Update the packaged mailbox manager skill so agents choose the right maintained command.

**Non-Goals:**

- Do not replace the existing all-account `clear-messages` command.
- Do not add a Stalwart mailbox administration lane.
- Do not expose participant-local mutable state through structural `messages list|get`.
- Do not implement account clearing as a local `deleted` flag; the message should no longer be structurally visible to that account.
- Do not rewrite canonical message documents to redact the cleared account from historical recipient metadata retained for other visible accounts.

## Decisions

### Command shape: add `messages clear --address`

Add account-scoped clearing under the existing structural message namespace:

```text
houmao-mgr mailbox messages clear --address <full-address> [--mailbox-root <path>] [--dry-run] [--yes]
houmao-mgr project mailbox messages clear --address <full-address> [--dry-run] [--yes]
```

This keeps account-scoped message operations together with `messages list|get`. The root-wide command remains:

```text
houmao-mgr mailbox clear-messages [--mailbox-root <path>] [--dry-run] [--yes]
houmao-mgr project mailbox clear-messages [--dry-run] [--yes]
```

Alternative considered: `mailbox accounts clear-messages --address`. That ties the command to account lifecycle more than message visibility and is less consistent with the existing message inspection surface.

### Destructive semantics: clear visibility, not mark deleted

The account-scoped clear operation removes the selected registration's projection rows and projection artifacts, then clears that registration's mailbox-local message/thread state. It does not simply set `is_deleted`. Structural message listing is driven by projections, so a state flag would leave the message visible in `messages list`.

Alternative considered: reuse mailbox-state mutation to mark every message deleted. That would be less destructive, but it would not solve the operator problem: clearing an account from the structural mailbox root.

### Shared artifact liveness: delete only after the last projection

The managed mailbox layer should compute one deterministic target set before mutation:

1. Resolve the active registration for `--address`.
2. Load all projection rows for that registration.
3. Plan removal of those projection artifacts and selected account local state.
4. For each selected message id, determine whether any projection for another registration will remain after removing the selected registration's projections.
5. Only for message ids with no remaining projections, plan deletion of the shared `messages` row, canonical message file, unreferenced managed-copy attachment artifacts, and orphaned shared message index state.

External `path_ref` attachment targets remain outside the clear scope. Managed-copy attachment artifacts are mailbox-owned and can be removed only when no retained message references them.

Alternative considered: delete the selected message's canonical file whenever the selected account had a projection. That would corrupt other accounts' visible mail and break sender `sent` history for recipient-only clears.

### Locking: prefer correctness over narrow concurrency

The first implementation should use the existing mailbox lock machinery and may acquire locks for all active registrations in the mailbox root while planning and applying the account-scoped clear. That is conservative, matches the shared canonical-artifact risk, and avoids races with delivery, repair, or another clear operation while the liveness decision is being made.

Future work can narrow locks to the selected account plus accounts sharing selected message ids if that becomes necessary.

### Payload shape: reuse cleanup result records

The account-scoped clear operation should return the same high-level cleanup payload families used by existing cleanup and root-wide clear commands:

- `planned_actions` for dry-run,
- `applied_actions` for applied removals,
- `blocked_actions` for unsafe paths or failed removals,
- `preserved_actions` for registrations, retained shared canonical artifacts, retained other-account projections, and external attachment targets when useful.

The scope should distinguish this operation from the all-account clear, for example:

```json
{
  "kind": "mailbox_account_message_clear",
  "mailbox_root": "/repo/.houmao/mailbox",
  "address": "alice@houmao.localhost",
  "registration_id": "..."
}
```

## Risks / Trade-offs

- [Risk] Canonical files may be deleted while another account still references them. -> Mitigate by deriving canonical deletion only from post-clear projection liveness and by covering multi-recipient and sender-history cases in tests.
- [Risk] Shared attachment rows can outlive deleted messages. -> Mitigate by cleaning mailbox-owned managed-copy artifacts only when their attachment rows have no remaining message references, and preserving external path refs.
- [Risk] Local mailbox SQLite state can drift from shared projections. -> Mitigate by clearing the selected account's local message/thread tables as part of the account clear and keeping repair as the recovery path for inconsistent roots.
- [Risk] All-registration locking limits concurrency. -> Accept initially because this is an operator destructive maintenance command, not a hot-path delivery operation.
- [Risk] The project wrapper might accidentally fall back to a shared global mailbox root. -> Reuse the existing project mailbox selected-overlay resolution helpers and cover this with wrapper parity tests.

## Migration Plan

No stored-data migration is required. Existing mailbox roots remain valid. The new command removes selected account visibility when invoked; existing all-account clear behavior remains unchanged.

Rollback is straightforward: remove the new CLI wrapper and managed account-clear entry point. Mailbox roots already cleared by the new operation remain valid and can receive new mail through the existing delivery path.

## Open Questions

None.
