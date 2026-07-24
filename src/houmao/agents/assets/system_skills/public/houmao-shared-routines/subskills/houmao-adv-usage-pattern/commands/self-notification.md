# Self-Notification

## Workflow

1. **Validate invocation context**. Preserve the actor posture, selected target, operation intent, and predecessor evidence supplied by the owning skill.
2. **Resolve required inputs**. Recover explicit values from current context and stop or ask when a required value remains missing.
3. **Execute the detailed procedure below**. Follow its ordering, gates, side-effect boundary, owned references, and output contract.
4. **Validate and report**. Return changed or inspected artifacts, evidence, blockers, and the command-specific stop condition.

If the request does not map cleanly to these steps, use the native planning tool to build a step-by-step plan from this command procedure, its owning skill constraints, available references, and the user request, then execute the plan.

Use this pattern family when a Houmao-managed agent wants to remind itself about later work and needs to choose the right reminder mechanism.

There are two supported modes:

- live gateway reminders through `/v1/reminders`,
- self-mail reminders that re-enter through ordinary open-mail processing.

## How To Choose

Prefer live gateway reminders when:

- the task is high-priority and the agent should stay focused on it first,
- the agent wants behavior like "ignore other new mail and work on this first",
- the reminder should not mix with newly arrived open mailbox traffic,
- one-off scheduling, repeating cadence, ranking, or pause behavior is useful.

Prefer self-mail when:

- the reminder backlog must survive gateway shutdown or restart,
- it is acceptable for later rounds to see the reminder together with newly arrived open mail,
- the agent may legitimately decide that some new external mail is more important than the old self-reminder.

If you are not sure and durable recovery is not explicitly required, prefer live gateway reminders.

## Multi-Step Rule

For multi-step work, keep the detailed checklist in local todo or scratch state and use one reminder per major work chunk rather than one reminder per tiny substep.

The reminder should tell the later round to reopen that local working state instead of duplicating the whole plan in reminder text.

## Modes

- Read [self-notification-via-reminders.md](self-notification-via-reminders.md) for the focus-first live gateway reminder mode.
- Read [self-wakeup-via-self-mail.md](self-wakeup-via-self-mail.md) for the durable and inbox-integrated self-mail mode.

## Guardrails

- Do not treat gateway reminders and self-mail as interchangeable without checking the focus-versus-durability trade-off.
- Do not choose self-mail by default when the task really wants focused live reminder behavior.
- Do not choose live gateway reminders when the reminder must survive gateway shutdown or restart.
