# Self-Notification Via Self-Mail

Use this mode within the broader self-notification pattern family when a Houmao-managed agent already has an active mailbox binding and wants its reminder backlog to survive gateway shutdown or restart.

Use gateway reminders instead when the work is high-priority, should stay focused ahead of unrelated new incoming mail, or when the richer live reminder controls on `/v1/reminders` are the better fit.

## When To Choose This Mode

Choose self-mail when:

- the reminder backlog must survive gateway shutdown or restart,
- it is acceptable for later rounds to see the self-reminder together with newly arrived unread mail,
- the agent may legitimately decide to work on some newly arrived external mail first when it next re-enters through open-mail triage.

Do not choose this mode by default merely because a later reminder is needed. If durable recovery is not explicitly required, prefer live gateway reminders.

## Why Use This Pattern

Use self-mail reminders when the agent needs a lightweight durable backlog that can survive ordinary short-term execution problems better than relying on one uninterrupted provider turn.

This pattern is especially useful for:

1. Mitigating LLM connection issues such as temporary network loss, upstream overload, or short-lived rate limiting. Unread self-mail preserves the next-step intent so a later round can resume instead of depending on one fragile live turn.
2. Mitigating provider early-stop behavior. Some providers may force the agent to stop after a maximum turn budget, output budget, or tool-call budget; self-reminder mail lets the agent continue the larger task as a fresh later turn.
3. Handling accidental interruption. If the operator briefly interrupts the agent for temporary work, or another direct prompt arrives through a surface such as tmux `send-keys`, the agent can return later and continue from the pending self-reminder instead of relying on volatile conversational momentum alone.
4. Supporting user-requested long-running or effectively unbounded work loops. When the operator explicitly wants the agent to keep working until manually stopped, self-reminder mail provides one durable way to keep re-queueing the next step so progress can continue across many separate turns instead of depending on one very long provider run.

This does not make the loop autonomous forever by itself. It is still bounded by notifier delivery, mailbox state, and the operator's decision to stop or redirect the agent.

For multi-step work, prefer keeping the detailed step list in one local todo file, scratchpad, or other agent-local working state and sending one self-mail reminder that tells the later round to reopen that local todo state. Do not create one mailbox reminder per tiny substep unless separate mailbox-level scheduling is actually needed.

## Workflow

1. Confirm the current mailbox identity and live gateway posture when the prompt does not already provide them.
2. For multi-step tasks, first write or refresh the detailed local todo list or working notes that the later round should continue from.
3. Use `houmao-agent-email-comms` to send one or more messages to the agent's own mailbox address. Prefer one self-mail item that points back to the local todo list or working notes rather than one message per small step. Each open self-mail item should usually represent one reminder, one continuation prompt, or one planned major step.
4. Give every self-reminder an informative, recognizable subject prefix so later rounds can quickly distinguish internal wake-up reminders from ordinary inbound mail sent by external agents or operators.
5. Use `houmao-agent-gateway` to keep gateway mail-notifier polling enabled.
6. Stop and wait for the next notifier-driven round.
7. When the next gateway notification arrives, use `houmao-process-emails-via-gateway` for that round.
8. In each later round, inspect the open inbox set, choose the self-mail item or items relevant to that round, reopen the referenced local todo list or working notes when applicable, and complete that work.
9. Treat those self-reminders as part of ordinary open-mail triage: if newly arrived external mail is more important now, it is acceptable to handle that first and leave the self-reminder unarchived for a later round.
10. After one self-mail item is fully complete, archive that completed reminder so it leaves the open mailbox backlog.
11. Leave unfinished or deferred self-mail unarchived so later rounds can pick it up.

## Self-Mail Template

Use one compact self-mail item per planned wake-up step when possible. For multi-step work, prefer one self-mail item per major work chunk, with the detailed checklist kept locally. The subject should make the message obviously recognizable as an internal reminder rather than ordinary inbound mail:

```text
Subject: [self-wakeup] <short next step>

Wake-up reason:
<why this needs a later round>

When to resume:
<trigger, dependency, or rough timing>

Next action:
<the exact first action to take when this self-mail is picked up, including reopening any local todo list if needed>

Done condition:
<what counts as complete so this reminder can be deleted>

Notes:
<optional context, constraints, or links to prior message refs>
```

Keep the body short enough that a later notifier-driven round can decide quickly whether to act on it, defer it, or leave it unread.

Use a stable marker such as `[self-wakeup]`, `[self-reminder]`, or another clearly internal prefix consistently across all reminder messages for the same workflow.

## Skill Boundary

- Use `houmao-agent-email-comms` for mailbox `status`, `list`, `peek`, `read`, `send`, `reply`, and `archive`.
- Use `houmao-agent-gateway` for gateway attach or discovery, gateway mail-notifier control, and optional direct reminders. Let that skill choose attach posture; for tmux-backed managed sessions its lifecycle guidance is foreground-first and treats background gateway execution as explicit user intent.
- Use `houmao-process-emails-via-gateway` when the notifier round actually arrives and you need the round-oriented open-mail workflow.

## Durability Boundary

- Unread self-mail is the durable work backlog for this pattern.
- Gateway mail-notifier polling is the live re-entry trigger while a compatible gateway remains attached and running.
- Direct gateway `/v1/reminders` can help with live timing, but they are optional timing assistance and not the durable backlog for this pattern.
- Do not describe this pattern as guaranteed unfinished-work recovery across gateway shutdown, gateway restart, or managed-agent instance replacement.
- Completed self-reminders are not durable backlog and should be pruned so they do not jam later mailbox inspection.
- This mode intentionally mixes self-reminders with newly arrived unread mail, so later rounds may reprioritize against external incoming mail instead of blindly resuming the self-reminder first.

## Guardrails

- This pattern depends on the filesystem mailbox transport keeping self-addressed self-mail unread until the agent explicitly mutates or removes that mailbox-local state.
- For multi-step work, prefer one self-reminder that points to a local todo list over many mailbox reminders for individual substeps.
- Use informative self-reminder titles so later rounds can distinguish internal backlog items from new external mail without opening every unread message first.
- Do not describe this mode as the best choice for "ignore other new mail and work on this first"; that is the live gateway reminder mode.
- Do not imply that background gateway execution is the default setup for this pattern.
- Prefer deleting completed self-reminders when the available supported mailbox surface allows it.
- If deletion is not available on the current supported mailbox surface, archive a completed self-reminder.
- Do not archive deferred, failed, or only partially completed self-mail items.
- Do not treat the advanced pattern as a replacement for ordinary one-step mailbox or gateway actions.
- Do not confuse mailbox backlog with gateway liveness: unread mail persists as the intent backlog, while notifier and reminders are live attached-gateway behavior.
