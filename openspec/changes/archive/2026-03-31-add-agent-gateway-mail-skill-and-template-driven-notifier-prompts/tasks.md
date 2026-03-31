## 1. Runtime-Owned Mailbox Skill Layout

- [x] 1.1 Add the packaged `houmao-email-via-agent-gateway` mailbox skill asset tree with a thin `SKILL.md`, action subdocuments, and curl-first endpoint references.
- [x] 1.2 Rename projected Houmao-owned mailbox skills to the `houmao-<skillname>` convention and update runtime mailbox skill projection helpers so mailbox-enabled sessions receive the common gateway skill alongside the active transport-specific mailbox skill.
- [x] 1.3 Revise the filesystem and Stalwart mailbox skills to the `houmao-email-via-filesystem` and `houmao-email-via-stalwart` naming convention and delegate shared `/v1/mail/*` operations to the common gateway skill while keeping transport-specific context and fallback guidance.
- [x] 1.4 Extend `houmao-mgr agents join` to install Houmao-owned mailbox skills into the adopted tool home by default, preserve unrelated user skills, and expose an explicit opt-out.
- [x] 1.5 Ensure Houmao-owned mailbox skill docs and references preserve the explicit `houmao` trigger wording rather than shortened or implicit names.

## 2. Gateway Notifier Prompt Rendering

- [x] 2.1 Add a packaged Markdown notifier prompt template asset for mailbox wake-ups with placeholder fields for resolver guidance, skill paths, curl examples, and unread summary content.
- [x] 2.2 Replace the hardcoded notifier prompt assembly in `gateway_service.py` with runtime string replacement over the packaged template.
- [x] 2.3 Change the unread prompt payload builder to render header summaries for all unread messages in the current unread snapshot instead of nominating only one target.
- [x] 2.4 Change notifier prompt guidance to tell the agent to use the installed `houmao-email-via-agent-gateway` skill for the mailbox turn and to use `pixi run houmao-mgr agents mail resolve-live` plus `gateway.base_url` as the ordinary discovery contract.
- [x] 2.5 Make notifier prompt rendering respect joined-session skill-install opt-out so prompts only claim installed Houmao mailbox skills when that installation actually occurred.
- [x] 2.6 Ensure notifier prompt text includes the explicit keyword `houmao` whenever it intends to trigger a Houmao-owned skill.

## 3. Verification

- [x] 3.1 Update gateway notifier unit tests to assert template-driven unread-summary prompts, gateway skill references, and manager-owned resolver guidance.
- [x] 3.2 Update mailbox system skill projection tests to assert that `email-via-agent-gateway` and its action/reference documents are projected into mailbox-enabled brain homes.
- [x] 3.3 Add joined-session coverage for default Houmao mailbox skill installation, opt-out behavior, and failure-closed handling when the adopted tool home cannot be updated safely.
- [x] 3.4 Run focused lint and test coverage for mailbox runtime support, gateway notifier prompt rendering, join-time skill projection, and runtime-owned mailbox skill projection.
