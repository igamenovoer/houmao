## Why

The current gateway mail notifier treats reminder eligibility as unread-set deduplication plus coarse gateway idleness. In practice that lets local interactive sessions receive a second reminder while the provider TUI is not truly ready for input, and it suppresses later reminders for unchanged unread mail even when earlier reminders were interrupted or abandoned by operator activity.

## What Changes

- Revise gateway mail notifier readiness so reminder enqueueing requires a strong live readiness check, not just tmux-session connectivity and an empty internal queue.
- Revise notifier triggering from unread-set deduplication to readiness-gated repeated reminders: if unread mail still exists and the TUI becomes ready again, the gateway may remind again even when the unread snapshot is unchanged.
- **BREAKING** Remove the current spec allowance for unchanged unread sets to suppress duplicate reminders merely because a prior reminder for that unread snapshot was already sent or enqueued.
- Preserve the existing prompt shape that summarizes all unread message headers in one reminder prompt and lets the agent choose which messages to inspect and handle.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `agent-gateway-mail-notifier`: change notifier polling, readiness, and reminder-repeat requirements from unread-set deduplication to strong readiness-gated reminders.
- `agent-gateway`: change the cross-cutting gateway notifier wake-up semantics from unread-set dedup behavior to level-triggered reminder behavior gated only by live prompt readiness.

## Impact

- Affected code: gateway notifier poll loop, local interactive gateway readiness inspection, notifier bookkeeping, and prompt-enqueue conditions under `src/houmao/agents/realm_controller/gateway_service.py`.
- Affected tests: gateway notifier unit and integration coverage, especially cases that currently assert `dedup_skip` for unchanged unread snapshots.
- Affected docs/specs: `openspec/specs/agent-gateway-mail-notifier/spec.md`, `openspec/specs/agent-gateway/spec.md`, and any demo or operator docs that currently describe unread-set deduplication as intended behavior.
