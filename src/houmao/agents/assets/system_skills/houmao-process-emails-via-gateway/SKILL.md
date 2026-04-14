---
name: houmao-process-emails-via-gateway
description: Use Houmao's round-oriented workflow for processing gateway-notified open inbox mail through a prompt-provided gateway base URL, gateway-API-first triage, selective inspection, post-success archive behavior, and stop-after-round discipline.
license: MIT
---

# Houmao Process Emails Via Gateway

Use this Houmao skill when a notifier or operator prompt tells you there is open shared-mailbox inbox work to process through a live gateway facade and already provides the exact gateway base URL for the current round.

This is the round-oriented workflow skill. Use `houmao-agent-email-comms` when you need the lower-level endpoint-discovery fallback, the exact `/v1/mail/*` request contract, or transport-local no-gateway guidance for ordinary mailbox actions inside the round.

## Workflow

1. Confirm the current prompt or mailbox context already provides the exact gateway base URL for this round.
2. If that base URL is missing, stop and report that the notifier round is missing required gateway bootstrap. Do not rediscover it inside this workflow.
3. Use `GET /v1/mail/status` when you need to confirm mailbox identity or current gateway availability for the round.
4. Use `POST /v1/mail/list` to list open inbox mail and current mailbox state for the round.
5. Start from open-mail metadata such as sender identity, subject, timestamps, `message_ref`, `thread_ref`, read state, and answered state.
6. Check whether any open emails correspond to work you already started in an earlier round but left stalled or interrupted.
7. When such stalled or interrupted work exists, continue that work in this round before treating unrelated open mail as new work.
8. Decide which open emails are relevant to process in this round.
9. Inspect only the selected emails needed to decide and perform the work for this round.
10. For each selected email, determine up front whether it needs a reply and remember the reply-required `message_ref`.
11. If the current prompt requests reply hardening, create one lowest-priority one-off gateway reminder for each reply-required email and remember its `reminder_id`.
12. Complete the requested work for the selected emails.
13. For selected emails that need a reply, send the reply through `POST /v1/mail/reply` only after the requested work succeeds.
14. When a reply succeeds through the normal end-of-round path, remove any not-yet-fired reply-hardening reminder for that email.
15. Archive only the successfully processed selected emails, and only after any required reply for that email succeeds.
16. Stop after the round and wait for the next notification. Do not proactively poll for more mail on your own.

## Selection Guidance

- Start with metadata-first triage. Do not treat every open inbox email as automatically in scope for the current round.
- If one or more open emails represent work you were already handling before you stalled or were interrupted, treat those emails as continuation candidates first.
- It is acceptable to continue multiple interrupted email-driven tasks in the same round when they are all still relevant and feasible.
- It is acceptable to defer unrelated open emails for a later round.
- Track reply-required emails separately from archive updates so required replies are sent after work completion and before archive.
- The notifier prompt tells you open inbox work exists; use the shared gateway mailbox API to list the actual open set for this round.
- If you need the exact gateway route contract for `status`, `list`, `peek`, `read`, `send`, `reply`, `mark`, `move`, or `archive`, use the installed Houmao skill `houmao-agent-email-comms`.
- Use the transport-local guidance inside `houmao-agent-email-comms` only for transport-specific context or no-gateway fallback.

## Reply Hardening

Use reply hardening when the current prompt asks for extra assurance around replying, for example: "must remember to reply", "harden reply action", "use reminder to make sure you remember to reply", or similar wording.

When reply hardening is requested:

1. After identifying a selected email as reply-required, create a gateway reminder for that email before doing the longer processing work and remember the returned `reminder_id`.
2. Use a one-off prompt reminder, not a repeat reminder.
3. Use `start_after_seconds=15` by default unless the prompt specifies a different reminder delay.
4. Append the reminder to the current reminder set as lowest priority. With the managed CLI surface, use `--after-all`. With direct gateway HTTP, first inspect current reminders and set `ranking` to one greater than the current maximum ranking.
5. Include enough email context in the reminder prompt to identify the required reply: `message_ref`, `thread_ref` when available, sender, subject, and the intended reply obligation.
6. Make the reminder prompt explicitly re-check whether the email has already been replied to; if it has not, send the reply through `POST /v1/mail/reply`; if it has already been replied to, do not send a duplicate reply.
7. If the normal end-of-round path sends the reply before the reminder fires, remove the hardening reminder with `houmao-mgr agents gateway reminders remove ... --reminder-id <reminder_id>` or `DELETE /v1/reminders/{reminder_id}`.
8. Keep the reminder scoped to reply assurance only. It must not archive the message unless the work and any required reply have succeeded.

## Reply-Hardening Reminder Template

Use this prompt template for each hardening reminder. Fill every bracketed field that is known at creation time and keep unknown optional fields explicit as `unknown`.

```text
Reply hardening reminder.

Mail: <message_ref>; thread: <thread_ref or unknown>; from: <sender>; subject: <subject>
Reply to: <reply recipient>

If this mail is still being processed and the work is not done, set this same one-off reminder again through the gateway with 15s and continue processing the email.

If this mail is already processed, reply to mail <message_ref>.
```

For direct gateway creation, use this one-off prompt reminder shape and replace `1001` with a ranking that appends after all current reminders:

```json
{
  "schema_version": 1,
  "reminders": [
    {
      "title": "Reply required: <subject>",
      "mode": "one_off",
      "prompt": "<filled reminder prompt from the template above>",
      "ranking": 1001,
      "paused": false,
      "start_after_seconds": 15
    }
  ]
}
```

## Guardrails

- Do not guess the gateway host or port; use the exact gateway base URL provided in the current round context.
- Do not switch to `houmao-mgr agents mail resolve-live` inside this notifier-round workflow when the base URL is missing; treat that as a contract failure for the current round.
- Do not archive an email before the corresponding work succeeds.
- Do not archive a reply-required email before its reply succeeds.
- Do not create repeat reminders for reply hardening; use one-off reminders only.
- Do not use repeat-reminder `interval_seconds` for reply hardening; use one-off reminder timing with `start_after_seconds`, defaulting to `15` unless the prompt specifies otherwise.
- Do not replace or rerank existing reminders when reply hardening asks for append behavior; append after all existing reminders.
- Do not send a duplicate reply from a hardening reminder without first checking whether the reply has already been sent.
- Do not leave a not-yet-fired reply-hardening reminder live after the normal path successfully sends the reply.
- Do not archive deferred, skipped, or unfinished emails.
- Do not abandon open continuation work merely because newer unrelated open mail also exists.
- Do not keep polling for more mail after the round completes; wait for the next gateway notification.
- Treat upstream gateway polling, open-mail snapshot updates, and mailbox-selection rules as outside your concern once the current round is complete.
