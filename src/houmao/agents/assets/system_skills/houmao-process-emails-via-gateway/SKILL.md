---
name: houmao-process-emails-via-gateway
description: Use Houmao's round-oriented workflow for processing gateway-notified unread emails through a prompt-provided gateway base URL, gateway-API-first triage, selective inspection, post-success mark-read behavior, and stop-after-round discipline.
license: MIT
---

# Houmao Process Emails Via Gateway

Use this Houmao skill when a notifier or operator prompt tells you there are unread shared-mailbox emails to process through a live gateway facade and already provides the exact gateway base URL for the current round.

This is the round-oriented workflow skill. Use `houmao-agent-email-comms` when you need the lower-level endpoint-discovery fallback, the exact `/v1/mail/*` request contract, or transport-local no-gateway guidance for ordinary mailbox actions inside the round.

## Workflow

1. Confirm the current prompt or mailbox context already provides the exact gateway base URL for this round.
2. If that base URL is missing, stop and report that the notifier round is missing required gateway bootstrap. Do not rediscover it inside this workflow.
3. Use `GET /v1/mail/status` when you need to confirm mailbox identity or current gateway availability for the round.
4. Use `POST /v1/mail/check` to list unread mail and current mailbox state for the round.
5. Start from unread metadata such as sender identity, subject, timestamps, `message_ref`, and `thread_ref`.
6. Check whether any unread emails correspond to work you already started in an earlier round but left stalled or interrupted.
7. When such stalled or interrupted work exists, continue that work in this round before treating unrelated unread mail as new work.
8. Decide which unread emails are relevant to process in this round.
9. Inspect only the selected emails needed to decide and perform the work for this round.
10. Complete the requested work for the selected emails.
11. Mark only the successfully processed selected emails read.
12. Stop after the round and wait for the next notification. Do not proactively poll for more mail on your own.

## Selection Guidance

- Start with metadata-first triage. Do not treat every unread email as automatically in scope for the current round.
- If one or more unread emails represent work you were already handling before you stalled or were interrupted, treat those emails as continuation candidates first.
- It is acceptable to continue multiple interrupted email-driven tasks in the same round when they are all still relevant and feasible.
- It is acceptable to defer unrelated unread emails for a later round.
- The notifier prompt tells you unread work exists; use the shared gateway mailbox API to list the actual unread set for this round.
- If you need the exact gateway route contract for `status`, `check`, `read`, `send`, `reply`, or `mark-read`, use the installed Houmao skill `houmao-agent-email-comms`.
- Use the transport-local guidance inside `houmao-agent-email-comms` only for transport-specific context or no-gateway fallback.

## Guardrails

- Do not guess the gateway host or port; use the exact gateway base URL provided in the current round context.
- Do not switch to `houmao-mgr agents mail resolve-live` inside this notifier-round workflow when the base URL is missing; treat that as a contract failure for the current round.
- Do not mark an email read before the corresponding work succeeds.
- Do not mark deferred, skipped, or unfinished emails read.
- Do not abandon unread continuation work merely because newer unrelated unread mail also exists.
- Do not keep polling for more mail after the round completes; wait for the next gateway notification.
- Treat upstream gateway polling, unread snapshot updates, and mailbox-selection rules as outside your concern once the current round is complete.
