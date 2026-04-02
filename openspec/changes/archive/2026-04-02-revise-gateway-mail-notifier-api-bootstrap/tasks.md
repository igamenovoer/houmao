## 1. Revise gateway notifier prompting

- [x] 1.1 Update the packaged mail notifier prompt template to announce unread mailbox work without embedding unread email summaries.
- [x] 1.2 Update the notifier prompt renderer to remove unread-summary substitution, remove `pixi`/resolver guidance, and include the exact live base URL plus full `/v1/mail/status`, `/v1/mail/check`, `/v1/mail/send`, `/v1/mail/reply`, and `/v1/mail/state` URLs.
- [x] 1.3 Update notifier prompt tests to assert the new prompt contract, including the absence of unread summaries and `pixi` references.

## 2. Revise runtime-owned mailbox system skills

- [x] 2.1 Update `houmao-process-emails-via-gateway` so notifier-driven rounds assume a prompt-provided base URL, list unread mail through the gateway API, and treat missing base URL as a contract failure.
- [x] 2.2 Update `houmao-email-via-agent-gateway` and its action/reference docs so they use context-provided gateway URLs first, fall back to `houmao-mgr agents mail resolve-live` only when needed, and remove all `pixi` references.
- [x] 2.3 Update transport-specific mailbox skills and supporting references to align with the revised gateway/bootstrap rules without duplicating legacy `pixi`-based discovery wording.

## 3. Verify projected skill and workflow behavior

- [x] 3.1 Update mailbox skill projection and join-install tests to assert the revised projected skill content and manual fallback wording.
- [x] 3.2 Update notifier and mailbox workflow integration tests to cover the new API-first round behavior and prompt-provided base URL contract.
- [x] 3.3 Run the targeted mailbox and gateway test suite and confirm the change is implementation-ready.
