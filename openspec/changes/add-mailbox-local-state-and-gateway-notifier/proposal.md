## Why

The current filesystem mailbox design stores mutable mailbox-view state in the shared mailbox-root SQLite index even though read, starred, archived, and deleted state are really per-mailbox concerns. We now want the gateway to poll unread mail reliably and notify idle agents, which makes it a good time to move recipient-local state into each mailbox's own SQLite database and keep gateway polling state separate from mailbox truth.

## What Changes

- Add a gateway-owned mail notifier capability that can be enabled or disabled through gateway HTTP endpoints, polls unread mail on an interval, and submits a runtime-owned notification turn only when the managed agent is idle.
- Strengthen the gateway running-log contract so `gateway.log` becomes an operator-facing disk log that can be tailed to watch notifier polling, busy retries, queue actions, and lifecycle behavior.
- Add per-mailbox SQLite state under each resolved mailbox directory so read or unread and related mailbox-view flags are stored per agent rather than in the shared mailbox-root SQLite index.
- **BREAKING** Redefine the shared mailbox-root SQLite index as shared catalog state only; recipient-local mutable state such as read, starred, archived, deleted, and unread thread summaries moves to per-mailbox SQLite.
- Update mailbox runtime bindings and system-skill guidance so `AGENTSYS_MAILBOX_FS_SQLITE_PATH` remains the shared-root catalog binding, new explicit local-mailbox bindings are added, and agents mark messages read after processing without depending on gateway presence.
- Update mailbox managed scripts and repair flows so delivery, state mutation, and recovery keep shared catalog state and per-mailbox state consistent without introducing aggregate recipient-status mirrors.

## Capabilities

### New Capabilities
- `agent-gateway-mail-notifier`: Gateway-managed periodic unread-mail polling, notifier enable or disable control, idle-only notification turns, and notifier runtime state.

### Modified Capabilities
- `agent-gateway`: Extend the gateway HTTP and durable-state contract to host notifier control and status alongside the existing request queue and lifecycle behavior.
- `agent-mailbox-fs-transport`: Move per-mailbox mutable state out of the shared mailbox-root SQLite index into a local SQLite database under each resolved mailbox directory.
- `agent-mailbox-system-skills`: Expand mailbox env bindings and runtime-owned mailbox skill guidance so agents can inspect local mailbox state and mark processed mail as read explicitly.
- `filesystem-mailbox-managed-scripts`: Update managed helper responsibilities so delivery, mailbox-state mutation, and repair operate across shared catalog state plus per-mailbox local state.

## Impact

- Affected code: `src/houmao/agents/realm_controller/gateway_*`, `src/houmao/agents/mailbox_runtime_*`, `src/houmao/mailbox/*`, runtime mailbox skill assets, and mailbox helper scripts under `src/houmao/mailbox/assets/rules/scripts/`.
- Affected APIs and contracts: gateway HTTP routes, gateway persisted state and running-log behavior, mailbox env vars, mailbox on-disk layout, and managed mailbox helper behavior.
- Affected docs and tests: gateway reference docs, mailbox reference docs, gateway runtime tests, mailbox transport tests, and migration coverage for old shared-root mailbox state.
