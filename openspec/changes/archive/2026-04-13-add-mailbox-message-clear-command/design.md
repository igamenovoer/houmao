## Context

The filesystem mailbox transport separates durable mailbox account registration from delivered mail content. Account metadata lives in `mailbox_registrations`, delivered content lives under `messages/<YYYY-MM-DD>/`, mailbox-visible projections live in registered mailbox folders, shared structural indexes live in `index.sqlite`, and each registered mailbox keeps local view state in `mailbox.sqlite`.

Existing lifecycle commands intentionally do not provide a whole-mail reset. `mailbox cleanup` removes inactive or stashed registrations while preserving canonical messages, and `mailbox unregister --mode purge` removes one account registration's projection/state without deleting canonical history. Operators therefore need either unsupported filesystem edits or a full mailbox root rebuild when they want to clear delivered mail while keeping accounts.

## Goals / Non-Goals

**Goals:**

- Provide a maintained `clear-messages` command for generic and project-scoped filesystem mailbox roots.
- Remove delivered message content and derived state while preserving mailbox account registrations and mailbox directories.
- Keep the command safe for destructive use through dry-run reporting and explicit confirmation.
- Keep `mailbox cleanup` and `mailbox unregister` semantics unchanged.
- Update system-skill and reference documentation so agents route this request through the maintained command.

**Non-Goals:**

- Do not add a Stalwart mailbox cleanup lane.
- Do not unregister accounts, delete mailbox directories, or remove private symlink mailbox target directories.
- Do not delete external `path_ref` attachment targets.
- Do not clear staging by default; staged content is not delivered mail and remains owned by repair/staging cleanup behavior.
- Do not add per-account or filtered deletion in this change.

## Decisions

### Decision: Add a new `clear-messages` command instead of extending `cleanup`

The existing `cleanup` contract is explicitly registration-focused and non-message-destructive. A new verb makes the destructive reset visible in help output and keeps existing automation that runs cleanup from accidentally deleting delivered mail.

Alternative considered: add `mailbox cleanup --messages`. Rejected because it overloads a safe maintenance verb with a much broader destructive behavior.

### Decision: Clear messages by shared index and registered mailbox state, not by deleting the whole mailbox root

The implementation should add a mailbox-managed helper that:

- snapshots active, inactive, and stashed registration metadata,
- acquires mailbox locks before mutation,
- deletes canonical message records and dependent shared rows,
- removes canonical message files under `messages/`,
- removes projection artifacts from registered mailbox folders,
- resets each registered mailbox's local `mailbox.sqlite` `message_state` and `thread_summaries`,
- clears shared `thread_summaries`,
- removes managed-copy attachment artifacts under the mailbox root's managed attachment directory when they are referenced by cleared messages,
- preserves all registration rows and mailbox account directory structure.

This keeps the operation aligned with the mailbox data model rather than relying on broad directory deletion.

Alternative considered: remove `messages/` and run `mailbox repair`. Rejected because repair treats canonical messages as the content authority. After deleting canonical messages, repair cannot know which mailbox-local state or managed attachment artifacts should be reset, and direct deletion would leave stale local mailbox state until repair or runtime paths touch each account.

### Decision: Treat confirmation as required for apply mode

The CLI should support `--dry-run` and `--yes`. In apply mode without `--yes`, interactive terminals should prompt before destructive clearing; non-interactive terminals should fail clearly and tell the operator to rerun with `--yes` or `--dry-run`.

Alternative considered: make `clear-messages` apply immediately because the verb is explicit. Rejected because the command deletes delivered history across all accounts, so it should follow the same safety posture as other destructive mailbox replacement paths.

### Decision: Keep the project command as a thin wrapper

`houmao-mgr project mailbox clear-messages` should resolve the selected overlay mailbox root with the same project mailbox root logic as the other project mailbox commands, then call the same shared helper used by `houmao-mgr mailbox clear-messages`.

Alternative considered: implement separate project-specific clearing logic. Rejected because the destructive semantics are root-local and should not diverge by entrypoint.

### Decision: Report cleanup-style structured output

The command should use the existing cleanup payload shape where practical, with scope fields that identify `mailbox_message_clear`, the resolved mailbox root, and counts or actions for canonical messages, projections, mailbox-local state, shared index rows, and managed attachments. Dry-run output should report planned actions without mutating the filesystem or SQLite state.

Alternative considered: return a minimal `{ok: true}` payload. Rejected because this command is destructive and operators need enough detail to audit what was planned or removed.

## Risks / Trade-offs

- [Risk] Clearing while delivery or state mutation is active could leave inconsistent state. -> Mitigation: acquire the existing address locks for known registrations plus the shared index lock, then re-read the index inside the lock before applying changes.
- [Risk] Removing external attachment paths could delete user files. -> Mitigation: only remove managed-copy attachment artifacts that resolve under the mailbox root's managed attachment directory; never remove external `path_ref` targets.
- [Risk] Symlink or private mailbox registrations could point outside the root. -> Mitigation: preserve registration directories and remove only known projection artifacts recorded in the shared index or mailbox-owned placeholder folders.
- [Risk] A partial filesystem failure could leave stale files after the SQLite transaction. -> Mitigation: make the operation idempotent and report blocked actions; rerunning should remove remaining stale message artifacts without unregistering accounts.
- [Risk] Operators may confuse message clearing with registration cleanup. -> Mitigation: keep command names and docs explicit: `cleanup` is registration cleanup; `clear-messages` is delivered-message reset.

## Migration Plan

No data migration is required. Existing mailbox roots remain valid; the new command is opt-in and only mutates roots when explicitly invoked.

Rollback is straightforward: remove the new CLI command, helper, docs, skill action, and tests. Roots already cleared by the command cannot recover deleted delivered messages unless the operator has an external backup.

## Open Questions

- Should a future change add narrower filters such as `--address`, `--before`, or `--older-than-seconds`, or should this command remain a whole-root reset only?
- Should staging cleanup eventually be folded into a separate explicit command such as `clear-staging`, or remain under the existing repair cleanup options?
