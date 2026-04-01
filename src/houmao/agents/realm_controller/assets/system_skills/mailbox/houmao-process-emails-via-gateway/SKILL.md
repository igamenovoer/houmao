---
name: houmao-process-emails-via-gateway
description: Use Houmao's round-oriented workflow for processing gateway-notified unread emails through metadata-first triage, selective inspection, post-success mark-read behavior, and stop-after-round discipline.
license: MIT
---

# Houmao Process Emails Via Gateway

Use this Houmao skill when a notifier or operator prompt tells you there are unread shared-mailbox emails to process through a live gateway facade.

This is the round-oriented workflow skill. Use `houmao-email-via-agent-gateway` when you need the lower-level resolver, endpoint, or `/v1/mail/*` request contract.

## Workflow

1. Run `pixi run houmao-mgr agents mail resolve-live`.
2. Confirm the resolver returns `gateway.base_url` for the current live shared mailbox facade.
3. Start from unread metadata such as sender identity, subject, timestamps, `message_ref`, and `thread_ref`.
4. Decide which unread emails are relevant to process in this round.
5. Inspect only the selected emails needed to decide and perform the work for this round.
6. Complete the requested work for the selected emails.
7. Mark only the successfully processed selected emails read.
8. Stop after the round and wait for the next notification. Do not proactively poll for more mail on your own.

## Selection Guidance

- Start with metadata-first triage. Do not treat every unread email as automatically in scope for the current round.
- It is acceptable to defer unrelated unread emails for a later round.
- If you need the exact gateway route contract for `check`, `read`, `send`, `reply`, or `mark-read`, open `skills/mailbox/houmao-email-via-agent-gateway/SKILL.md`.
- Use the current transport-specific Houmao mailbox skill under `skills/mailbox/` only for transport-local context or no-gateway fallback.

## Guardrails

- Do not guess the gateway host or port; use `gateway.base_url` from `pixi run houmao-mgr agents mail resolve-live`.
- Do not mark an email read before the corresponding work succeeds.
- Do not mark deferred, skipped, or unfinished emails read.
- Do not keep polling for more mail after the round completes; wait for the next gateway notification.
- Treat upstream gateway polling, unread snapshot updates, and mailbox-selection rules as outside your concern once the current round is complete.
