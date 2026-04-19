## 1. Local SQLite Access Layer

- [x] 1.1 Inventory all filesystem mailbox `ATTACH DATABASE` call sites in `managed.py` and `gateway_mailbox.py`, and classify each as multi-account, single-account read, or single-account mutation.
- [x] 1.2 Replace `_attached_local_mailboxes_with_options()` with direct mailbox-local connection helpers that prepare one registration's `mailbox.sqlite`, optionally replace unreadable local state during repair, and return a narrow local-state context.
- [x] 1.3 Refactor local-state SQL helpers to use direct local connections and unqualified `message_state` / `thread_summaries` table names instead of shared-connection schema aliases.
- [x] 1.4 Preserve existing mailbox-local schema initialization, unreadable-local-state backup behavior, and symlink-resolved local SQLite path handling.

## 2. Managed Filesystem Mailbox Flows

- [x] 2.1 Update `ensure_mailbox_local_state()` to iterate active registrations and seed or rebuild each mailbox-local database without attaching more than one local database to any shared connection.
- [x] 2.2 Update `deliver_message()` so shared structural delivery commits under the existing lock discipline, then affected mailbox-local databases are updated one registration at a time with idempotent local writes.
- [x] 2.3 Update lazy mailbox-state insertion and mark/read/reply state mutation paths to use direct local connections while preserving current read, answered, archived, box, and self-addressed unread semantics.
- [x] 2.4 Update `repair_mailbox_index()` to rebuild local mailbox state one account at a time, including unreadable local database replacement, without attaching all recovered registrations.
- [x] 2.5 Ensure local-state update failures after committed structural changes raise explicit mailbox operation errors that identify repair as the recovery path.

## 3. Gateway Filesystem Mailbox Flows

- [x] 3.1 Refactor filesystem gateway list, peek, and read paths to query the current account's local `mailbox.sqlite` directly and use shared `index.sqlite` separately for canonical paths and metadata.
- [x] 3.2 Refactor filesystem gateway move, mark, and archive paths to mutate the current account's local `mailbox.sqlite` directly while keeping shared projection updates under the existing locking and validation behavior.
- [x] 3.3 Remove remaining filesystem mailbox `ATTACH DATABASE` usage unless a call site is intentionally retained with documented justification and cannot affect account or fanout capacity.

## 4. Regression Coverage

- [x] 4.1 Add a unit test that registers at least eleven active filesystem mailbox accounts and verifies all-account local-state initialization succeeds.
- [x] 4.2 Add a unit test that delivers one message to enough recipients for sender plus recipients to exceed ten unique affected accounts, then verifies shared projections and mailbox-local unread/read state for all affected accounts.
- [x] 4.3 Add a unit test that repairs a mailbox root with more than ten discovered accounts and verifies rebuilt local state remains queryable.
- [x] 4.4 Keep or update existing tests for self-addressed mail, reply answering, archive/move behavior, symlink-local state preservation, and unreadable local database repair.
- [x] 4.5 Add or update gateway filesystem mailbox tests to verify list/read/move behavior after removing single-account `ATTACH` usage.

## 5. Documentation And Validation

- [x] 5.1 Update mailbox internals or reference documentation if it currently implies shared and mailbox-local SQLite are updated through attached databases.
- [x] 5.2 Run `pixi run test tests/unit/mailbox/test_managed.py` and the focused gateway mailbox test module or tests touched by the change.
- [x] 5.3 Run `pixi run lint` and `pixi run typecheck`.
- [x] 5.4 Confirm `rg "ATTACH DATABASE" src/houmao/mailbox src/houmao/agents/realm_controller/gateway_mailbox.py` no longer shows filesystem mailbox implementation dependence on SQLite attachment capacity.

Validation notes:

- `pixi run test tests/unit/mailbox/test_managed.py` expands through the Pixi task to `python -m pytest tests/unit tests/unit/mailbox/test_managed.py`; that broad run currently has four unrelated failures outside the mailbox/gateway change. `pixi run python -m pytest tests/unit/mailbox/test_managed.py` passes.
- `pixi run typecheck` currently reports only pre-existing strict mypy errors in `src/houmao/agents/assets/system_skills/houmao-utils-llm-wiki/scripts/`.
