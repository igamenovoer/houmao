## 1. Gateway Mail Surface

- [x] 1.1 Extend gateway models and client code with typed payloads and responses for `GET /v1/mail/status`, `POST /v1/mail/check`, `POST /v1/mail/send`, and `POST /v1/mail/reply`.
- [x] 1.2 Add the new `/v1/mail/*` routes to the gateway service, keep `POST /v1/requests` limited to `submit_prompt` and `interrupt`, and make the mailbox routes unavailable when the gateway listener is bound to `0.0.0.0`.
- [x] 1.3 Implement gateway-side mailbox adapter selection from `attach.json -> manifest.json -> launch_plan.mailbox`, with explicit failures when no mailbox binding or usable adapter can be constructed and with one cached adapter instance per attached session.

## 2. Filesystem Mailbox Adapter

- [x] 2.1 Define a `Protocol`-based gateway mailbox adapter interface in a dedicated gateway-mailbox support module, then extract or wrap the existing filesystem mailbox behavior behind that interface for shared `status`, `check`, `send`, and `reply`.
- [x] 2.2 Normalize filesystem mailbox results to the shared contract, including opaque `message_ref` values and shared message metadata instead of direct SQLite details.
- [x] 2.3 Add fabricated filesystem mailbox fixtures that exercise gateway mailbox reads, sends, replies, and unread discovery without requiring launched-agent flows.

## 3. Stalwart Mailbox Adapter

- [x] 3.1 Extend `MailboxTransport` to include `stalwart`, replace the filesystem-shaped mailbox binding models with transport-discriminated declarative and resolved bindings plus per-transport redacted manifest serialization, and persist a secret-free `stalwart` binding that the gateway can reload later.
- [x] 3.2 Implement Stalwart provisioning helpers for domain, account, and mailbox credential setup with idempotent reuse behavior, secret-free `credential_ref` persistence, and no unnecessary credential churn unless a later explicit refresh path is added.
- [x] 3.3 Implement a raw-HTTP JMAP-backed Stalwart mailbox adapter using the repository's existing synchronous HTTP stack for shared `status`, `check`, `send`, and `reply` behavior that returns the same normalized gateway mailbox contract as the filesystem adapter.

## 4. Gateway Notifier Integration

- [x] 4.1 Rewrite gateway notifier unread polling to use the shared gateway mailbox facade instead of reading filesystem mailbox-local SQLite directly.
- [x] 4.2 Keep notifier bookkeeping, deduplication, and audit persistence separate from transport-owned mailbox read state while updating `_build_mail_notifier_prompt()` and related reminder wording to stay transport-neutral.
- [x] 4.3 Cover notifier idle-only enqueue rules, busy deferral, deduplication, and poll errors for both filesystem-backed and Stalwart-backed mailbox adapters.

## 5. Runtime And Mailbox Contract Updates

- [x] 5.1 Update runtime mailbox config parsing and binding support so gateway and direct mailbox paths can both resolve filesystem and `stalwart` bindings from the manifest contract, publish secret-free credential references through runtime-managed env bindings, and replace hard-reject guards with transport dispatch where appropriate.
- [x] 5.2 Update projected mailbox skill guidance and runtime-owned mailbox prompt construction so shared mailbox operations prefer the live gateway mailbox facade when present and preserve direct transport fallback otherwise, explicitly refactoring `prepare_mail_prompt()` and `ensure_mailbox_command_ready()` for transport-aware behavior.
- [x] 5.3 Update gateway and mailbox reference docs to describe the new `/v1/mail/*` routes, the shared `message_ref` contract, and the gateway-to-mail-system implementation focus for this change.

## 6. Focused Verification

- [x] 6.1 Add focused gateway tests that fabricate `attach.json` plus `manifest.json` inputs and verify mailbox route behavior without launched-agent roundtrips.
- [x] 6.2 Add focused Stalwart-backed tests that provision isolated test mailboxes, perform gateway `check` or `send` or `reply` flows, and verify normalized results without full runtime session bring-up, using a test-scoped Stalwart server fixture or mocked management or JMAP HTTP surfaces as appropriate.
- [x] 6.3 Run targeted gateway and mailbox test suites plus `pixi run openspec validate --strict --json --type change add-stalwart-mailbox-transport`.
