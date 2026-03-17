# Feature Request: Filesystem Mailbox Principal Deregistration and Leave Cleanup

## Status
Resolved on 2026-03-17.

## Resolution Summary
The filesystem mailbox lifecycle now includes managed deregistration flows (`deactivate` and `purge`) plus documented active, inactive, and stashed registration states for leave and cleanup handling.

## Summary
Add an explicit filesystem-mailbox leave-group and principal-deregistration workflow so agents and operators can remove a participant from a shared mail group in a consistent, protocol-defined way.

The current mailbox protocol defines how a principal joins a shared mailbox root and how managed scripts handle delivery, mailbox-state mutation, repair, and interrupted-write staging cleanup. It does not yet define what should happen when a participant leaves the group, which means agents currently have no authoritative cleanup contract for deregistration, historical mailbox views, or principal-registry retention.

## Why
Current behavior has a clear gap:
- `add-agent-mailbox-protocol` defines join semantics for in-root mailbox directories and symlink-registered private mailbox directories.
- The managed helper surface under `rules/scripts/` covers delivery, mailbox-state mutation, and repair or reindex.
- The transport explicitly validates principal registration during delivery and fails if a principal mailbox registration is missing or invalid.

What is missing is equally important:
- no defined "leave group" operation,
- no managed script for principal deregistration,
- no retention policy for `mailboxes/<principal>` after departure,
- no rule for whether `principals` rows in `index.sqlite` should be deleted, tombstoned, or retained,
- no contract for whether historical inbox or sent projections should remain visible, be pruned, or be quarantined,
- no rule for how symlink-registered principals should be removed safely versus in-root principals.

Without a defined cleanup path, the likely outcomes are inconsistent operator practices, agents guessing at destructive cleanup, and ambiguous recovery when a participant should stop receiving future deliveries but past conversation history must remain auditable.

## Requested Scope
1. Define the canonical meaning of "leave the group" for a filesystem mailbox principal.
2. Decide the retention policy for historical content:
   - whether canonical messages remain untouched,
   - whether old inbox or sent projections remain,
   - whether mailbox-state rows are retained, tombstoned, or removed,
   - whether `principals` rows become inactive rather than deleted.
3. Define behavior separately for:
   - in-root mailbox registrations under `mailboxes/<principal>/`,
   - symlink-registered private mailbox directories under `mailboxes/<principal> -> ...`.
4. Add a managed, mailbox-local cleanup surface under `rules/scripts/` so agents and operators can perform the defined deregistration flow consistently rather than improvising filesystem and SQLite mutations.
5. Define safety behavior when:
   - the principal still has unread mail,
   - the principal still has active runtime sessions,
   - the mailbox registration is already missing or partially broken,
   - the mailbox path is symlinked to a private directory outside the shared root.
6. Decide whether the leave operation should be reversible, such as by preserving an inactive registry row that can be reactivated later.
7. Document the operator and agent-facing contract in the filesystem mailbox spec, design notes, and mailbox skill guidance.

## Acceptance Criteria
1. The filesystem mailbox protocol explicitly defines the expected cleanup behavior when a participant leaves a shared mail group.
2. A managed command or script exists for the defined leave-group or deregistration operation, and it is part of the mailbox-local helper contract under `rules/scripts/`.
3. The leave workflow is explicit about what happens to:
   - `mailboxes/<principal>`,
   - the `principals` registry row in `index.sqlite`,
   - historical `mailbox_state` rows,
   - historical inbox and sent projections,
   - canonical messages under `messages/`.
4. Behavior is defined and tested for both in-root principals and symlink-registered principals.
5. The workflow is idempotent or clearly reports that the principal is already removed or inactive.
6. Failure modes are explicit for active-session conflicts, invalid registration state, and unsafe destructive cleanup attempts.
7. Docs explain when to use the managed cleanup flow instead of manual filesystem or SQLite edits.

## Non-Goals
- No requirement to delete canonical messages that are shared conversation history by default.
- No requirement to define shared-claim or multi-consumer mailbox semantics in the same change.
- No requirement to solve cross-host mailbox migration.
- No requirement to redesign the existing delivery, repair, or mailbox-state update flows beyond what is needed to support principal deregistration safely.

## Suggested Follow-Up
- Create an OpenSpec change focused on filesystem mailbox principal deregistration and leave-group cleanup.
- Decide whether the protocol should model departure as hard removal, soft deactivation, or both.
- Add a managed script and tests for the selected behavior.
- Update the mailbox Q&A and operator docs once the cleanup contract is finalized.
