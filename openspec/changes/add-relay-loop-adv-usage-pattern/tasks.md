## 1. Advanced Pattern Assets

- [x] 1.1 Update `src/houmao/agents/assets/system_skills/houmao-adv-usage-pattern/SKILL.md` to list the relay-loop pattern and its trigger conditions alongside the existing self-notification entry.
- [x] 1.2 Add a new relay-loop pattern page under `src/houmao/agents/assets/system_skills/houmao-adv-usage-pattern/patterns/` that documents the loop roles, queued gateway handoff flow, receipt email flow, final-result email flow, and final-result acknowledgement flow.
- [x] 1.3 In the new relay-loop pattern page, document the required local ledger fields, explicit `loop_id` and `handoff_id` usage, default storage under `HOUMAO_JOB_DIR`, check-mail-first resend behavior, receiver deduplication rule, and the rule that senders arm follow-up then end the current round.
- [x] 1.4 In the new relay-loop pattern page, state explicitly that `HOUMAO_MEMORY_DIR` is not the default home for mutable relay-loop bookkeeping.
- [x] 1.5 In the new relay-loop pattern page, document how timing thresholds are sourced: derive from task context and explicit user deadlines when available, and ask the user when a materially important value cannot be chosen sensibly from context.
- [x] 1.6 In the new relay-loop pattern page, document the default supervision model for many outbound loops: one supervisor reminder, one local ledger, and optional self-mail checkpoint rather than one live reminder per active loop.
- [x] 1.7 In the new relay-loop pattern page, add concrete text-block templates for downstream handoff request text, mailbox follow-up messages, supervisor reminder text, and optional self-mail checkpoint text, including the timing fields that must be recorded.

## 2. Validation

- [x] 2.1 Update `docs/reference/gateway/operations/mail-notifier.md` so it matches the current source-truth notifier behavior, including the current repeat-notification behavior for unchanged unread mail.
- [x] 2.2 Update `tests/unit/agents/test_system_skills.py` to assert that the new relay-loop pattern asset is packaged and referenced from the advanced-usage skill index.
- [x] 2.3 Update any affected projected-skill or brain-builder assertions so the new advanced-usage asset set remains validated after packaging.
