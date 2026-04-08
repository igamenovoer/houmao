## 1. Advanced Pattern Assets

- [ ] 1.1 Update `src/houmao/agents/assets/system_skills/houmao-adv-usage-pattern/SKILL.md` to list the relay-loop pattern and its trigger conditions alongside the existing self-notification entry.
- [ ] 1.2 Add a new relay-loop pattern page under `src/houmao/agents/assets/system_skills/houmao-adv-usage-pattern/patterns/` that documents the loop roles, queued gateway handoff flow, receipt email flow, final-result email flow, and final-result acknowledgement flow.
- [ ] 1.3 In the new relay-loop pattern page, document the required local ledger fields, explicit `loop_id` and `handoff_id` usage, check-mail-first resend behavior, receiver deduplication rule, and the rule that senders arm follow-up then end the current round.
- [ ] 1.4 In the new relay-loop pattern page, document the default supervision model for many outbound loops: one supervisor reminder, one local ledger, and optional self-mail checkpoint rather than one live reminder per active loop.
- [ ] 1.5 In the new relay-loop pattern page, add concrete text-block templates for downstream handoff request text, mailbox follow-up messages, supervisor reminder text, and optional self-mail checkpoint text.

## 2. Validation

- [ ] 2.1 Update `docs/reference/gateway/operations/mail-notifier.md` so it matches the current source-truth notifier behavior, including the current repeat-notification behavior for unchanged unread mail.
- [ ] 2.2 Update `tests/unit/agents/test_system_skills.py` to assert that the new relay-loop pattern asset is packaged and referenced from the advanced-usage skill index.
- [ ] 2.3 Update any affected projected-skill or brain-builder assertions so the new advanced-usage asset set remains validated after packaging.
