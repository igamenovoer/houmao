## 1. Revise the notifier prompt contract

- [x] 1.1 Update the mail notifier template and renderer so the prompt starts with a full unread-email summary section for the current snapshot and explicitly instructs the agent to use `houmao-process-emails-via-gateway`.
- [x] 1.2 Ensure the unread-email summary section includes all unread messages, keeps only non-body metadata, and the later operations section renders the exact live gateway base URL plus full `/v1/mail/check|send|reply|state` endpoint URLs.
- [x] 1.3 Update notifier prompt tests for multi-message summaries, no-body-content summaries, joined-session skill-install opt-out behavior, and full dynamic endpoint URL rendering.

## 2. Add the round-oriented mailbox workflow skill

- [x] 2.1 Add the projected runtime-owned mailbox skill `skills/mailbox/houmao-process-emails-via-gateway/` with workflow guidance for metadata-first triage, relevant-message selection, inspection, work execution, post-success mark-read, and stop-after-round behavior.
- [x] 2.2 Revise `houmao-email-via-agent-gateway` and the transport-specific mailbox skills so they clearly support the new workflow skill instead of duplicating its round-oriented guidance.
- [x] 2.3 Update mailbox skill projection and join-install coverage so mailbox-enabled sessions receive the new skill wherever Houmao-owned mailbox skills are installed by default.

## 3. Verify notifier-driven round behavior and related guidance

- [x] 3.1 Add or update tests that cover round-bounded processing behavior, including selecting task-relevant emails, leaving deferred emails unread, and marking only successfully processed emails read.
- [x] 3.2 Update any demo, fixture, or operator-facing expectations that currently assert the old notifier prompt wording or the old `houmao-email-via-agent-gateway`-first wake-up contract.
