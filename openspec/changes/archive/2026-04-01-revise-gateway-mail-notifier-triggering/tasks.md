## 1. Align notifier enqueueing with live prompt readiness

- [x] 1.1 Add a notifier-ready decision path in the gateway runtime that reuses the strongest backend-owned prompt-readiness signal instead of treating local tmux connectivity as sufficient readiness.
- [x] 1.2 Update local interactive or other TUI-backed notifier gating so reminder enqueueing requires the same idle-and-ready-for-input posture already enforced by direct prompt control.
- [x] 1.3 Keep server-managed headless notifier gating aligned with its backend-owned “can accept prompt now” posture so notifier readiness stays consistent across gateway execution adapters.

## 2. Replace unread-set dedup suppression with readiness-gated repeated reminders

- [x] 2.1 Remove unread-set deduplication as a blocker in the notifier poll loop so unchanged unread mail remains eligible whenever the managed prompt surface becomes ready again.
- [x] 2.2 Keep notifier bookkeeping observational only by removing any behavioral dependence on persisted reminder-dedup or reminder-resolution state while preserving poll and notification timestamps plus per-poll audit evidence.
- [x] 2.3 Preserve the existing aggregated unread-snapshot reminder prompt shape so repeated reminders still list the current unread headers and let the agent choose which messages to inspect and handle.

## 3. Update regression coverage and operator-facing guidance

- [x] 3.1 Revise gateway notifier unit and integration tests to cover prompt-ready gating for TUI-backed sessions, repeated reminders for unchanged unread mail, and the operator-interruption case.
- [x] 3.2 Update notifier audit and log expectations so repeated eligibility is represented as repeated prompt-ready reminders rather than `dedup_skip` behavior for unchanged unread snapshots.
- [x] 3.3 Update demo or operator-facing docs that currently describe unread-set deduplication as intended notifier behavior.
