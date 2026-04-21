## 1. Notifier State

- [x] 1.1 Extend gateway mail-notifier runtime storage and migrations with durable bookkeeping for the currently remembered compacted eligible `message_ref` set.
- [x] 1.2 Update notifier record read/write helpers so compaction bookkeeping is kept separate from `last_notified_digest`, notification timestamps, and mailbox read-state semantics.

## 2. Notifier Runtime Behavior

- [x] 2.1 Update the gateway notifier polling cycle to prune remembered compacted refs to the current eligible set and run `pre_notification_context_action=compact` only when newly eligible mail appears.
- [x] 2.2 Ensure successful compaction records the current eligible set for the ongoing eligibility stretch, while failed compaction does not mark newly eligible mail as already compacted.
- [x] 2.3 Harden queued TUI notifier dispatch so `mail_notifier_prompt` participates in prompt-submission tracking and does not immediately reopen the surface for another compaction cycle.

## 3. Verification And Docs

- [x] 3.1 Add unit or integration regression coverage showing that unchanged eligible mail can survive repeated polling cycles without triggering repeated compaction.
- [x] 3.2 Add regression coverage showing that newly eligible mail added to an already-compacted eligible set triggers at most one additional compaction for the expanded set.
- [x] 3.3 Update `docs/reference/gateway/operations/mail-notifier.md` so the documented polling cycle and repeat-wake behavior reflect one-shot compaction per continuous eligibility stretch.
