## 1. Add mailbox-local state storage and migration

- [x] 1.1 Extend filesystem mailbox path and bootstrap logic so each resolved mailbox directory owns a stable `mailbox.sqlite` alongside the existing shared-root `index.sqlite`.
- [x] 1.2 Define and create the mailbox-local SQLite schema with mailbox-scoped `message_state` keyed by `message_id` and mailbox-local `thread_summaries` keyed by `thread_id`, and stop treating shared-root recipient-state tables or shared `thread_summaries.unread_count` as authoritative for new writes.
- [x] 1.3 Implement migration of legacy shared-root `mailbox_state` rows into per-mailbox `message_state` tables and rebuild mailbox-local thread summaries from migrated local state during bootstrap or repair for existing mailbox roots.
- [x] 1.4 Update repair flows so structural shared-root catalog state and mailbox-local state can both be rebuilt deterministically when one side is missing or stale, with any retained shared-root thread summary data treated as structural-only.

## 2. Move mailbox operations onto local mailbox state

- [x] 2.1 Update delivery flows so sender and recipient mailbox-local `message_state` rows and mailbox-local thread-summary caches are initialized in each mailbox's `mailbox.sqlite` while shared-root catalog data remains in `index.sqlite`.
- [x] 2.2 Update mailbox-state mutation helpers so read, starred, archived, and deleted changes target the addressed mailbox's local SQLite state instead of a shared aggregate recipient-state table.
- [x] 2.3 Update mailbox query paths and related tests so unread counts and thread summaries come from mailbox-local `thread_summaries` keyed by `thread_id`, preserve independent multi-recipient read behavior, and treat any shared-root thread-summary data as structural-only.

## 3. Publish the new mailbox runtime and skill contract

- [x] 3.1 Extend runtime mailbox bindings so `AGENTSYS_MAILBOX_FS_SQLITE_PATH` stays the shared-root `index.sqlite` binding while new `AGENTSYS_MAILBOX_FS_MAILBOX_DIR` and `AGENTSYS_MAILBOX_FS_LOCAL_SQLITE_PATH` bindings publish the resolved mailbox directory and mailbox-local SQLite path.
- [x] 3.2 Update projected filesystem mailbox skill assets and references so agents use the explicit local mailbox bindings, rely on shared helper scripts for steps that touch shared-root SQLite, mailbox-local SQLite, or locks, and only mark messages read after successful processing.
- [x] 3.3 Update runtime mailbox start, resume, and refresh flows so the new mailbox-local bindings remain stable across persisted manifests and binding refreshes.

## 4. Add the gateway mail notifier capability

- [x] 4.1 Extend gateway models, persistence, and HTTP routes with `PUT /v1/mail-notifier`, `GET /v1/mail-notifier`, and `DELETE /v1/mail-notifier` plus durable notifier configuration and status, while using `payload.launch_plan.mailbox` from the runtime-owned session manifest as the sole persisted notifier-support contract.
- [x] 4.2 Implement the gateway notifier poll loop so it reads unread state from mailbox-local SQLite, applies the idle-only busy rules, and records gateway-owned notifier bookkeeping separately from mailbox read state.
- [x] 4.3 Add the internal notifier request path and reminder prompt builder so unread-mail reminders execute through the existing serialized gateway worker model without exposing a new public request kind.
- [x] 4.4 Make `gateway.log` a stable tail-friendly running log that records gateway lifecycle, notifier poll decisions, busy retries, and execution outcomes with rate-limited repetitive polling messages.
- [x] 4.5 Reject notifier enablement explicitly when the attach contract has no readable runtime-owned manifest or the manifest launch plan has no mailbox binding, and cover notifier restart recovery, busy deferral, deduplication behavior, and running-log observability in gateway tests.

## 5. Update docs and verification

- [x] 5.1 Update mailbox and gateway reference docs to explain the shared catalog versus mailbox-local state split, mailbox-scoped `message_id` and `thread_id` identities, the manifest-backed notifier capability contract, notifier endpoints, the explicit mark-read-after-processing contract, and the operator-facing `gateway.log` tail-watch surface.
- [x] 5.2 Add or update unit and integration tests for mailbox migration, mailbox-scoped local state identity, independent recipient read state, mailbox-local repair, notifier polling, and notifier rejection on missing, unreadable, or mailbox-disabled manifests.
- [x] 5.3 Run targeted gateway and mailbox test suites plus `pixi run openspec validate --strict --json --type change add-mailbox-local-state-and-gateway-notifier`.
