## 1. Restructure The Advanced-Usage Self-Notification Pages

- [x] 1.1 Replace the current self-mail-only advanced self-wakeup entry with one self-notification pattern family page under `src/houmao/agents/assets/system_skills/houmao-adv-usage-pattern/`.
- [x] 1.2 Add or revise one mode-specific page for live gateway reminders that composes the existing `houmao-agent-gateway` reminder surface instead of restating raw API details.
- [x] 1.3 Move or revise the current self-mail pattern page so it is clearly one mode within the self-notification family rather than the only self-notification pattern.

## 2. Document The Selection Rules And Trade-Offs

- [x] 2.1 Document that live gateway `/v1/reminders` is the preferred mode for high-priority focused work, richer scheduling behavior, and the "do this before unrelated new mail" case.
- [x] 2.2 Document that self-mail is the preferred mode when durable backlog across gateway shutdown or restart is required or when later rounds may legitimately reprioritize against newly arrived unread mail.
- [x] 2.3 Document the default chooser rule that, if durability is not explicitly required, the agent should prefer `/v1/reminders`.
- [x] 2.4 Document the multi-step rule that detailed substeps stay in local todo or scratch state and that the self-notification mechanism should usually carry only one reminder per major work chunk.

## 3. Validate Packaged Skill Content

- [x] 3.1 Update packaged system-skill content tests to assert the new self-notification page structure and routing from the top-level `houmao-adv-usage-pattern` skill.
- [x] 3.2 Add or update content assertions that verify the advanced-usage guidance describes the reminder-versus-self-mail focus and durability trade-off honestly.
