---
name: houmao-process-emails-via-gateway
description: Use Houmao's round-oriented workflow for processing gateway-notified unread emails through a prompt-provided gateway base URL, gateway-API-first triage, selective inspection, post-success mark-read behavior, and stop-after-round discipline.
license: MIT
---

# Houmao Process Emails Via Gateway

Use this Houmao skill when a notifier or operator prompt tells you there are unread shared-mailbox emails to process through a live gateway facade and already provides the exact gateway base URL for the current round.

This is the round-oriented workflow skill. Use `houmao-email-via-agent-gateway` when you need the lower-level endpoint-discovery fallback or the exact `/v1/mail/*` request contract.

## Workflow

1. Confirm the current prompt or mailbox context already provides the exact gateway base URL for this round.
2. If that base URL is missing, stop and report that the notifier round is missing required gateway bootstrap. Do not rediscover it inside this workflow.
3. Use `GET /v1/mail/status` when you need to confirm mailbox identity or current gateway availability for the round.
4. Use `POST /v1/mail/check` to list unread mail and current mailbox state for the round.
5. Start from unread metadata such as sender identity, subject, timestamps, `message_ref`, and `thread_ref`.
6. Decide which unread emails are relevant to process in this round.
7. Inspect only the selected emails needed to decide and perform the work for this round.
8. Complete the requested work for the selected emails.
9. Mark only the successfully processed selected emails read.
10. Stop after the round and wait for the next notification. Do not proactively poll for more mail on your own.

## Selection Guidance

- Start with metadata-first triage. Do not treat every unread email as automatically in scope for the current round.
- It is acceptable to defer unrelated unread emails for a later round.
- The notifier prompt tells you unread work exists; use the shared gateway mailbox API to list the actual unread set for this round.
- If you need the exact gateway route contract for `check`, `read`, `send`, `reply`, or `mark-read`, open `skills/mailbox/houmao-email-via-agent-gateway/SKILL.md`.
- Use the current transport-specific Houmao mailbox skill under `skills/mailbox/` only for transport-local context or no-gateway fallback.

## Guardrails

- Do not guess the gateway host or port; use the exact gateway base URL provided in the current round context.
- Do not switch to `houmao-mgr agents mail resolve-live` inside this notifier-round workflow when the base URL is missing; treat that as a contract failure for the current round.
- Do not mark an email read before the corresponding work succeeds.
- Do not mark deferred, skipped, or unfinished emails read.
- Do not keep polling for more mail after the round completes; wait for the next gateway notification.
- Treat upstream gateway polling, unread snapshot updates, and mailbox-selection rules as outside your concern once the current round is complete.
