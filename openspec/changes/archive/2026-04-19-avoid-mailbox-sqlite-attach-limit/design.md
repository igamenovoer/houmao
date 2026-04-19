## Context

The filesystem mailbox transport stores shared structural state in one mailbox-root `index.sqlite` and stores each account's mutable mailbox-view state in that account's resolved `mailbox.sqlite`. This split is already part of the current spec: shared state owns registrations, messages, recipients, attachments, and projections, while mailbox-local state owns read, answered, archived, box, and local thread-summary state.

The current implementation couples those stores through SQLite `ATTACH DATABASE`. `src/houmao/mailbox/managed.py` attaches one local `mailbox.sqlite` per affected registration for all-account local-state initialization, multi-recipient delivery, lazy state insertion, and repair. SQLite in this environment is compiled with `MAX_ATTACHED=10`, and Python cannot raise a connection limit above that compiled ceiling. That means an otherwise valid mailbox root with more than ten active accounts, or one delivery touching more than ten unique sender/recipient accounts, can fail for an implementation detail that is not part of the mailbox model.

The right fix is to stop depending on multi-account attachment. A configured "maximum attached accounts" cap would preserve the bug as product behavior, and rebuilding SQLite with a larger limit would leave the design fragile across environments.

## Goals / Non-Goals

**Goals:**

- Support filesystem mailbox roots with more active accounts than SQLite's attached-database ceiling.
- Support delivery, initialization, and repair for affected account sets larger than SQLite's attached-database ceiling.
- Preserve the existing shared-root plus mailbox-local storage layout.
- Preserve deterministic address locking and explicit failure behavior.
- Keep local mailbox state repairable and idempotent so interrupted local-state writes can be repaired from shared structural state and canonical message files.
- Remove `ATTACH DATABASE` from filesystem mailbox implementation paths where practical, including single-account gateway operations, so no filesystem mailbox path depends on attached-database availability.

**Non-Goals:**

- Do not collapse all mailbox-local state into the shared root index.
- Do not add a hard account-count or recipient-count limit to work around SQLite.
- Do not require a custom SQLite build or new external database dependency.
- Do not change the public mailbox CLI, gateway API, message model, or on-disk root layout except for internal update ordering.
- Do not change Stalwart transport behavior.

## Decisions

### Use direct local SQLite connections instead of `ATTACH`

Replace `_attached_local_mailboxes_with_options()` with helpers that open one mailbox-local SQLite database directly for one registration, prepare or repair that local database as needed, run mailbox-local mutations against unqualified `message_state` and `thread_summaries` tables, then close the connection. Shared-root operations continue to use a separate `index.sqlite` connection.

Alternative considered: batch `ATTACH` operations below the compiled limit. This would unblock roots with more than ten accounts but keep the same fragile alias-based model and still require careful batch transaction boundaries. Direct local connections match the data ownership model more closely.

Alternative considered: increase SQLite's attached-database limit at runtime. This cannot exceed the compiled `MAX_ATTACHED` value and is therefore not portable.

### Treat mailbox-local state as independently updated, derived state

The shared index and canonical message files remain the authority for structural delivery. Mailbox-local rows are the authority for one mailbox's view state, but missing deterministic local rows for committed structural messages are repairable from shared message/projection state. Delivery should commit structural shared state first under the existing lock set, then update each affected mailbox-local database one at a time while locks are still held. If a later local write fails after the shared delivery commit, the operation should fail explicitly with enough context for repair, and repair/ensure flows must be able to rebuild the missing local rows idempotently.

Alternative considered: keep one all-or-nothing SQL transaction across shared and all local mailbox DBs. SQLite `ATTACH` is the mechanism that provided that shape, and it is exactly what creates the account ceiling. The filesystem mailbox already has canonical files, explicit lock files, and repair logic, so resilient repairable local state is a better fit.

### Refactor local-state helpers around registration and direct table names

Current helpers take a shared connection plus a schema alias such as `mailbox_local_3`. The implementation should introduce mailbox-local helpers that accept either a direct local `sqlite3.Connection` or a narrow local-state context containing the registration, local path, and local connection. Those helpers should cover:

- seeding or rebuilding local message state for one registration,
- clearing one local mailbox database,
- inserting or upserting one message-state row,
- rebuilding one local `thread_summaries` table,
- lazy insertion for an existing projected message,
- read/answered/archive/move state transitions.

This keeps SQL simple and makes it obvious when code is touching shared structural state versus account-local state.

### Keep locking at the mailbox-address layer

The implementation should preserve the existing address-lock ordering: acquire affected address locks in ascending full-address order before acquiring the index lock. For delivery, affected addresses are sender plus recipients. For all-account initialization or repair, affected addresses are all active or discovered addresses. Direct local connections should be opened and updated only while the same lock discipline protects the relevant mailbox paths.

### Remove gateway single-account `ATTACH` for consistency

Gateway filesystem mailbox operations currently attach only one local database, so they do not hit the ten-account ceiling directly. They should still be refactored to query the current account's local `mailbox.sqlite` directly and use shared `index.sqlite` separately for canonical paths and projection metadata. This keeps the filesystem mailbox implementation free of `ATTACH` as a design dependency and prevents future single-account paths from inheriting attach-specific assumptions.

### Verify with >10-account scenarios

Regression tests should create at least eleven active filesystem mailbox registrations because the local SQLite build exposes the historical limit at ten attached databases. Tests should cover:

- local-state initialization or bootstrap refresh with more than ten active accounts,
- one delivery whose sender plus recipients exceeds ten unique affected accounts,
- repair or rebuild with more than ten discovered accounts,
- gateway/list/read/move behavior after the refactor remains correct for a normal single account.

## Risks / Trade-offs

- [Risk] Shared structural delivery may commit before all mailbox-local state updates finish. → Mitigation: keep address locks held through local-state writes, make local writes idempotent, fail explicitly with repair guidance on local update failure, and ensure repair can rebuild deterministic local rows.
- [Risk] Refactoring alias-based SQL can accidentally change read, answered, archived, or self-addressed unread semantics. → Mitigation: retain existing behavior-focused tests and add targeted tests around self-addressed delivery, reply marking, archive/move, and repair.
- [Risk] Opening one local connection per affected account may be slower for very large fanout than one shared attached transaction. → Mitigation: correctness and portability take priority; fanout sizes are expected to be modest, and direct local writes avoid the hard SQLite ceiling.
- [Risk] Cross-store transactionality becomes less implicit. → Mitigation: document the authority boundary clearly in code and specs: shared structural state is committed through the shared index, mailbox-local state is independently maintained and repairable under the same address-lock discipline.

## Migration Plan

No on-disk migration is required. Existing mailbox roots already use shared `index.sqlite` plus per-account `mailbox.sqlite` files. The change replaces the access pattern used by Houmao-owned code.

Implementation should be deployable as a normal code update. Rollback remains possible because the schema and file layout do not change, but a rollback would reintroduce the SQLite attach ceiling.

## Open Questions

- Should a local-state update failure during delivery return a specialized repair hint or reuse the existing managed mailbox operation error text?
- Should repair report a count of local mailbox databases rebuilt separately from structural projection/message counts?
