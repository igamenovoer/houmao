# Self-Wakeup Via Self-Mail

Use this pattern when a Houmao-managed agent already has an active mailbox binding and a live gateway, wants to stage one or more later steps for itself, and wants later notifier-driven rounds to pick up that backlog.

## Workflow

1. Confirm the current mailbox identity and live gateway posture when the prompt does not already provide them.
2. Use `houmao-agent-email-comms` to send one or more messages to the agent's own mailbox address. Each unread self-mail item can represent one reminder, one continuation prompt, or one planned major step.
3. Use `houmao-agent-gateway` to keep gateway mail-notifier polling enabled.
4. Stop and wait for the next notifier-driven round.
5. When the next gateway notification arrives, use `houmao-process-emails-via-gateway` for that round.
6. In each later round, inspect the unread set, choose the self-mail item or items relevant to that round, complete that work, and mark only the successfully completed self-mail items read through `houmao-agent-email-comms`.
7. Leave unfinished or deferred self-mail unread so later rounds can pick it up.

## Skill Boundary

- Use `houmao-agent-email-comms` for mailbox `status`, `check`, `read`, `send`, `reply`, and `mark-read`.
- Use `houmao-agent-gateway` for gateway attach or discovery, gateway mail-notifier control, and optional direct wakeups.
- Use `houmao-process-emails-via-gateway` when the notifier round actually arrives and you need the round-oriented unread-mail workflow.

## Durability Boundary

- Unread self-mail is the durable work backlog for this pattern.
- Gateway mail-notifier polling is the live re-entry trigger while a compatible gateway remains attached and running.
- Direct gateway `/v1/wakeups` can help with live timing, but they are optional timing assistance and not the durable backlog for this pattern.
- Do not describe this pattern as guaranteed unfinished-work recovery across gateway shutdown, gateway restart, or managed-agent instance replacement.

## Guardrails

- This pattern depends on the filesystem mailbox transport keeping self-addressed self-mail unread until it is explicitly marked read.
- Do not mark deferred, failed, or only partially completed self-mail items read.
- Do not treat the advanced pattern as a replacement for ordinary one-step mailbox or gateway actions.
- Do not confuse mailbox backlog with gateway liveness: unread mail persists as the intent backlog, while notifier and wakeups are live attached-gateway behavior.
