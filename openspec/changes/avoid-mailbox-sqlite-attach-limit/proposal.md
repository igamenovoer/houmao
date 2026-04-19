## Why

Filesystem mailbox roots can exceed SQLite's default compiled attached-database ceiling because Houmao models each account as an independent mailbox with its own local `mailbox.sqlite`. The current implementation attaches one local database per affected account for bulk initialization, repair, and multi-recipient delivery, so mailbox roots or fanout deliveries can fail after roughly ten accounts even though the mailbox protocol does not define such a limit.

## What Changes

- Remove implementation dependence on multi-account SQLite `ATTACH DATABASE` for filesystem mailbox operations.
- Keep the shared root `index.sqlite` as the authoritative structural store for registrations, canonical messages, recipients, attachments, and projections.
- Treat each account-local `mailbox.sqlite` as independently opened mailbox-view state for that account, updated through direct local connections rather than through shared-connection aliases.
- Preserve deterministic address lock ordering and explicit repair semantics so interrupted local-state updates are detectable and recoverable.
- Add regression coverage for mailbox roots and message fanout with more than ten active accounts.
- Do not add a configured maximum account count or fanout count tied to SQLite `MAX_ATTACHED`.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `agent-mailbox-fs-transport`: Require filesystem mailbox operations to support roots and affected-account sets larger than SQLite's attached-database ceiling by avoiding multi-account `ATTACH DATABASE` dependence.

## Impact

- Affected code: `src/houmao/mailbox/managed.py`, especially local-state initialization, message delivery, lazy state insertion, and repair paths.
- Affected code: `src/houmao/agents/realm_controller/gateway_mailbox.py`, where filesystem gateway reads and moves currently attach one local mailbox database to the shared index connection.
- Affected tests: `tests/unit/mailbox/test_managed.py` and gateway mailbox tests for filesystem transport behavior.
- Affected docs/specs: filesystem mailbox transport requirements and any mailbox internals documentation that describes shared/root versus mailbox-local SQLite behavior.
