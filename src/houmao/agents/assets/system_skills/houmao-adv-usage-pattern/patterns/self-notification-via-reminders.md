# Self-Notification Via Gateway Reminders

Use this mode within the broader self-notification pattern family when a Houmao-managed agent already has a live gateway and wants a focused live reminder that does not get mixed into ordinary unread mailbox work.

Use self-mail instead when the reminder backlog must survive gateway shutdown or restart.

## When To Choose This Mode

Choose live gateway reminders when:

- the work is high-priority and should stay focused ahead of unrelated new incoming mail,
- the user wants behavior like "ignore other new mail and work on this first",
- the task benefits from one-off scheduling, repeating cadence, ranking, or pause behavior,
- durability across gateway restart is not required.

If you are unsure and durable recovery is not explicitly required, prefer this mode.

## Workflow

1. Confirm that a live gateway is attached and discover the exact `gateway.base_url` when the prompt does not already provide it.
2. For multi-step tasks, write or refresh the detailed local todo list or working notes first.
3. Use `houmao-agent-gateway` to create one or more live reminders through `/v1/reminders`.
4. Prefer one reminder per major work chunk rather than one reminder per tiny substep.
5. Give each reminder an informative title and prompt so the later round can understand the intended work immediately.
6. Use ranking when one reminder should stay ahead of others, and use repeat mode only when a repeating live reminder is genuinely needed.
7. When the reminder fires, reopen the referenced local todo list or working notes and continue that work.
8. Update or delete the reminder when it no longer represents the current next step.

## Reminder Shape

Keep the reminder concise and focused:

```text
Title: [focus-reminder] <short next step>
Prompt: Reopen <local todo or scratch state> and continue <major work chunk>.
Ranking: <smaller value = higher priority>
Mode: one_off | repeat
Paused: false
```

Use a stable title marker such as `[focus-reminder]` or `[self-reminder]` consistently for related reminders.

## Focus And Durability Boundary

- This mode does not mix with newly arrived unread mailbox traffic.
- That separation is what makes this mode the right fit for "work on this first" behavior.
- `/v1/reminders` is live gateway process state and does not survive gateway shutdown or restart.
- This mode is therefore richer for live scheduling, but weaker than self-mail for durable recovery.

## Guardrails

- Use `houmao-agent-gateway` for the exact reminder operations instead of restating raw gateway API details here.
- Do not describe this mode as durable across gateway stop or restart.
- Do not create many tiny reminders when one major-chunk reminder plus local todo state is enough.
- Do not use this mode when the reminder must survive gateway loss; use self-mail instead.
