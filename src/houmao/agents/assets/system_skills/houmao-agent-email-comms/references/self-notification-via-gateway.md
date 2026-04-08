# Self-Notification Through The Live Gateway

Use this pattern when a Houmao-managed agent already has a live gateway and mailbox binding, needs to leave itself one follow-up reminder, and wants that reminder to arrive through the normal gateway mail-notifier flow.

## Pattern

1. Confirm the current mailbox identity and live gateway posture for this turn.
2. Send one new message to the agent's own mailbox address with the exact follow-up instructions in the subject or body.
3. Ensure the live gateway mail-notifier is enabled through `houmao-agent-gateway`.
4. Return to an idle waiting posture and wait for the next gateway notification prompt.
5. When that notification prompt arrives, use `houmao-process-emails-via-gateway` for the notified unread-email round.
6. Mark the self-sent message read only after the follow-up work succeeds.

## When To Use It

Use this pattern when the goal is to leave one mailbox-driven follow-up task for the same managed agent and let the live gateway notify that agent later, rather than polling mail continuously or scheduling a separate gateway wakeup.

## Routing Boundary

- Use `houmao-agent-email-comms` for mailbox status and mailbox send work.
- Use `houmao-agent-gateway` for enabling, disabling, or inspecting the gateway mail-notifier.
- Use `houmao-process-emails-via-gateway` when the notification round actually arrives.

## Guardrails

- This pattern depends on a live attached gateway and an active mailbox binding.
- This is not durable recovery across gateway stop or restart; it is live gateway behavior.
- The gateway mail-notifier deduplicates by the unread-message set, so leaving the same unread self-message in place does not create an unlimited repeating reminder loop.
- Do not describe this as the same thing as direct gateway `/v1/wakeups`; mailbox self-notification is mailbox-driven, while wakeups are a separate gateway feature.
- Mark the self-sent message read only after the follow-up work succeeds.
