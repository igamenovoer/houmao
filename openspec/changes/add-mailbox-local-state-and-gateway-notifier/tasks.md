## 1. Add mailbox-local state storage and migration

- [ ] 1.1 Extend filesystem mailbox path and bootstrap logic so each resolved mailbox directory owns a stable `mailbox.sqlite` alongside the existing shared-root `index.sqlite`.
- [ ] 1.2 Define and create the mailbox-local SQLite schema for per-mailbox view state and local thread summaries, and stop treating shared-root recipient-state tables as authoritative for new writes.
- [ ] 1.3 Implement migration of legacy shared-root `mailbox_state` and summary data into per-mailbox `mailbox.sqlite` during bootstrap or repair for existing mailbox roots.
- [ ] 1.4 Update repair flows so structural shared-root catalog state and mailbox-local state can both be rebuilt deterministically when one side is missing or stale.

## 2. Move mailbox operations onto local mailbox state

- [ ] 2.1 Update delivery flows so sender and recipient mailbox-local state is initialized in each mailbox's `mailbox.sqlite` while shared-root catalog data remains in `index.sqlite`.
- [ ] 2.2 Update mailbox-state mutation helpers so read, starred, archived, and deleted changes target the addressed mailbox's local SQLite state instead of a shared aggregate recipient-state table.
- [ ] 2.3 Update mailbox query paths and related tests so unread counts and thread summaries come from mailbox-local state and preserve independent multi-recipient read behavior.

## 3. Publish the new mailbox runtime and skill contract

- [ ] 3.1 Extend runtime mailbox bindings so `AGENTSYS_MAILBOX_FS_SQLITE_PATH` stays the shared-root `index.sqlite` binding while new `AGENTSYS_MAILBOX_FS_MAILBOX_DIR` and `AGENTSYS_MAILBOX_FS_LOCAL_SQLITE_PATH` bindings publish the resolved mailbox directory and mailbox-local SQLite path.
- [ ] 3.2 Update projected filesystem mailbox skill assets and references so agents use the explicit local mailbox bindings, rely on shared helper scripts for steps that touch shared-root SQLite, mailbox-local SQLite, or locks, and only mark messages read after successful processing.
- [ ] 3.3 Update runtime mailbox start, resume, and refresh flows so the new mailbox-local bindings remain stable across persisted manifests and binding refreshes.

## 4. Add the gateway mail notifier capability

- [ ] 4.1 Extend gateway models, persistence, and HTTP routes with `PUT /v1/mail-notifier`, `GET /v1/mail-notifier`, and `DELETE /v1/mail-notifier` plus durable notifier configuration and status.
- [ ] 4.2 Implement the gateway notifier poll loop so it reads unread state from mailbox-local SQLite, applies the idle-only busy rules, and records gateway-owned notifier bookkeeping separately from mailbox read state.
- [ ] 4.3 Add the internal notifier request path and reminder prompt builder so unread-mail reminders execute through the existing serialized gateway worker model without exposing a new public request kind.
- [ ] 4.4 Make `gateway.log` a stable tail-friendly running log that records gateway lifecycle, notifier poll decisions, busy retries, and execution outcomes with rate-limited repetitive polling messages.
- [ ] 4.5 Reject notifier enablement explicitly for sessions without mailbox support and cover notifier restart recovery, busy deferral, deduplication behavior, and running-log observability in gateway tests.

## 5. Update docs and verification

- [ ] 5.1 Update mailbox and gateway reference docs to explain the shared catalog versus mailbox-local state split, notifier endpoints, the explicit mark-read-after-processing contract, and the operator-facing `gateway.log` tail-watch surface.
- [ ] 5.2 Add or update unit and integration tests for mailbox migration, independent recipient read state, mailbox-local repair, notifier polling, and notifier rejection on mailbox-disabled sessions.
- [ ] 5.3 Run targeted gateway and mailbox test suites plus `pixi run openspec validate --strict --json --type change add-mailbox-local-state-and-gateway-notifier`.
