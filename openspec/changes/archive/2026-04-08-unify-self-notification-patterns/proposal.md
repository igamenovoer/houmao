## Why

Houmao's advanced-usage skill currently documents self-notification only through self-mail plus gateway mail-notifier rounds. That is now incomplete because the live gateway already exposes `/v1/reminders`, which is a competing self-notification mechanism with different priority, scheduling, and durability trade-offs.

Agents and operators need one supported decision framework that explains when to use ranked gateway reminders versus self-mail backlog, instead of treating self-mail as the only advanced self-notification pattern or forcing callers to infer the trade-offs from unrelated gateway and mailbox pages.

## What Changes

- Reframe the advanced-usage self-notification guidance as one unified self-notification pattern with two supported modes: gateway reminders and self-mail reminders.
- Define explicit selection guidance:
  - use live gateway `/v1/reminders` when the task is high-priority, the agent should stay focused on that work first, or repeating or ranked reminder behavior is useful,
  - use self-mail reminders when the work should naturally mix with other incoming mail, or when the reminder must survive gateway shutdown or restart.
- State that `/v1/reminders` does not mix with newly arrived mail and therefore supports focused "work on this first" behavior, while self-mail intentionally re-enters through the unread mailbox flow and may be deprioritized behind other incoming mail.
- State that live gateway reminders are non-durable live gateway state, while self-mail unread state is the durable backlog that survives gateway failure.
- Define a default recommendation: if the caller is unsure and durable recovery is not explicitly required, prefer `/v1/reminders` because it supports richer one-off, repeating, ranking, and pause behavior.
- Restructure the advanced-usage skill pages so self-notification is presented as one subskill or pattern family with two different ways rather than as only one self-mail page.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `houmao-adv-usage-pattern-skill`: the advanced-usage skill requirements change from one self-mail-only self-wakeup page to one unified self-notification pattern that compares gateway reminders and self-mail, defines when to choose each, and documents the focus-versus-durability trade-off honestly.

## Impact

Affected areas are the packaged advanced-usage system-skill assets under `src/houmao/agents/assets/system_skills/houmao-adv-usage-pattern/` and the corresponding spec at `openspec/specs/houmao-adv-usage-pattern-skill/spec.md`. This change is documentation and skill-guidance only; it does not introduce new runtime APIs because `/v1/reminders` already exists.
