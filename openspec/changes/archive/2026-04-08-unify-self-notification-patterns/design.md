## Context

Houmao's advanced-usage skill currently documents self-notification only as self-mail plus gateway mail-notifier rounds. That guidance was reasonable when the main competing live self-notification surface was the older wakeup model, but the repository now ships ranked live gateway reminders at `/v1/reminders`.

That creates a real product-level choice for agents:

- live gateway reminders are isolated from ordinary incoming mail and support ranking, pause, one-off timing, and repeating cadence,
- self-mail reminders are durable unread mailbox backlog that survives gateway shutdown or restart, but they deliberately re-enter through ordinary unread-mail processing and therefore mix with other incoming mail.

The current advanced-usage skill does not give callers a supported decision framework for those trade-offs. As a result, the agent may overuse self-mail where focused reminder behavior is better, or overuse live reminders where durable backlog is required.

This change is confined to skill and spec guidance. The reminder API, mailbox API, and runtime behavior already exist and are not being redesigned here.

## Goals / Non-Goals

**Goals:**

- Present self-notification as one advanced-usage pattern family with two supported modes rather than one self-mail-only pattern.
- Define when to choose gateway reminders versus self-mail in operator and agent terms.
- Make the focus-versus-durability trade-off explicit:
  - gateway reminders for focused, high-priority, live work that should not mix with ordinary incoming mail,
  - self-mail for durable backlog that can survive gateway loss and can be re-triaged alongside new incoming mail.
- Preserve the boundary that the advanced-usage skill composes existing direct-operation skills rather than replacing them.
- Establish a default recommendation for the uncertain case that still respects the durability boundary.

**Non-Goals:**

- Changing `/v1/reminders` runtime behavior, ranking rules, or persistence semantics.
- Changing mailbox unread semantics, notifier logic, or reminder scheduling.
- Adding new CLI or managed-agent wrapper routes for reminders.
- Turning self-notification into a guaranteed autonomous recovery mechanism independent of mailbox and gateway state.

## Decisions

### 1. Self-notification becomes one pattern family with two explicit modes

The advanced-usage skill should present self-notification as one pattern family, not as two unrelated patterns and not as only one self-mail page.

The recommended structure is:

- one chooser page for self-notification,
- one mode-specific page for gateway reminders,
- one mode-specific page for self-mail reminders.

The chooser page owns the "which mechanism should I use?" decision. The mode-specific pages own the detailed operational guidance.

This is preferable to burying the comparison inside one long self-mail page because the comparison itself is the main missing behavior. It is also preferable to documenting the two modes as unrelated patterns because the user's mental model is one job: "remind myself later."

### 2. Gateway reminders are the focus-first mode

The advanced-usage guidance should treat `/v1/reminders` as the preferred mode when the agent wants focused live re-entry that does not compete with ordinary unread mailbox triage.

The page should explain that reminders:

- are delivered through the live gateway reminder slot rather than as unread mail,
- do not get mixed into the unread mailbox set,
- support richer control such as one-off scheduling, repeating cadence, ranking, and pause semantics.

This is what enables behaviors such as "ignore new inbound mail and work on this first." The advanced-usage page should say that explicitly instead of forcing the reader to infer it from the reminder API shape.

### 3. Self-mail is the durable and inbox-integrated mode

The advanced-usage guidance should treat self-mail as the mode to choose when the backlog must survive gateway shutdown or restart, or when it is acceptable and even desirable for the reminder to re-enter through ordinary mailbox triage.

The page should explain that self-mail:

- persists as unread mailbox backlog even if the gateway disappears,
- is intentionally mixed with other unread incoming mail during later notifier-driven rounds,
- therefore allows later rounds to choose whether the self-reminder is still the most important unread item.

This makes self-mail the better fit for durable work continuation, but the worse fit for "stay focused on this one thing ahead of everything else."

### 4. The default recommendation is reminder-first unless durability is explicitly needed

When the agent is unsure which self-notification mode to use, the advanced-usage skill should recommend `/v1/reminders` by default as long as durable recovery is not an explicit requirement.

That default is justified because reminders already offer the richer feature set:

- one-off and repeating scheduling,
- ranking,
- pause and blocking behavior,
- separation from ordinary mailbox unread traffic.

The guidance must immediately pair that default with the durability caveat: if the reminder must survive gateway crash or restart, self-mail is the correct mode instead.

### 5. Multi-step work should prefer local todo state plus one reminder per major chunk

The current self-mail page already trends in this direction, and the unified pattern should make it a clear rule across both modes.

For multi-step work, the detailed checklist belongs in local todo or scratch state. The self-notification mechanism should usually carry only the reminder to reopen that local working state.

This keeps both reminder lists and mailbox backlog manageable and avoids replacing structured local execution state with dozens of tiny reminders.

## Risks / Trade-offs

- [The new chooser page may duplicate lower-level reminder and mailbox instructions] → Keep the chooser page focused on selection logic and route detailed API or mailbox mechanics back to the gateway and mailbox subpages.
- [A reminder-first default may cause callers to miss the durability boundary] → State the non-durable live-gateway boundary immediately next to the default recommendation, not in a distant footnote.
- [Self-mail guidance may still be misused as one-message-per-substep backlog] → Make the local-todo-plus-one-reminder rule explicit in the chooser page and both mode pages.
- [Different pages could drift and give inconsistent advice] → Treat the chooser page as the authoritative decision surface and keep the mode-specific pages narrow and role-specific.

## Migration Plan

1. Add or revise the advanced-usage skill pages so self-notification is presented as one pattern family with two modes.
2. Move the current self-mail guidance under that family and update it to describe itself as the durable or inbox-integrated mode rather than the only mode.
3. Add the gateway-reminder mode page that composes the existing `houmao-agent-gateway` reminder guidance into the advanced-usage context.
4. Update the top-level advanced-usage `SKILL.md` to route readers through the self-notification family page.
5. Update packaged skill-content tests to assert the new page structure and the key selection guidance.

Rollback is documentation rollback only.

## Open Questions

None blocking. The current repository behavior is already clear enough to document:

- `/v1/reminders` is live and non-durable,
- self-mail unread state is durable,
- the two mechanisms differ primarily in focus isolation versus inbox-integrated durability.
