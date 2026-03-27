---
name: email-via-stalwart
description: Operate the Stalwart-backed mailbox transport for agents using runtime-provided email mailbox env vars and the live gateway mailbox facade when available.
license: MIT
---

# Email Via Stalwart

Use this skill when the runtime-selected mailbox transport is `stalwart`.

## Routine Actions With A Live Gateway Facade

- When a live loopback gateway exposes the shared `/v1/mail/*` facade for this session, treat that shared gateway surface as the default routine path for ordinary mailbox work.
- Ordinary attached-session mailbox work in this change means `check`, `send`, `reply`, and marking one processed message read.
- Prefer the shared gateway mailbox routes for those routine actions: `POST /v1/mail/check`, `POST /v1/mail/send`, `POST /v1/mail/reply`, and `POST /v1/mail/state`.
- Treat `message_ref` and `thread_ref` as opaque shared mailbox references. Do not derive raw Stalwart object identifiers or transport-local structure from the visible prefix.
- After you successfully process one nominated unread message, mark that same `message_ref` read through `POST /v1/mail/state` with `read=true`.
- Do not restate direct JMAP request recipes or filesystem helper flows as the default attached-session path when the shared gateway facade is available.

## Shared Gateway Route Quick Reference

- For routine attached-session turns, use these stable v1 request shapes directly instead of scanning repo docs or OpenAPI for contract rediscovery.
- `POST /v1/mail/check`
  `{"schema_version":1,"unread_only":true,"limit":10}`
- `POST /v1/mail/send`
  `{"schema_version":1,"to":["recipient@agents.localhost"],"subject":"...","body_content":"...","attachments":[]}`
- `POST /v1/mail/reply`
  `{"schema_version":1,"message_ref":"<opaque message_ref>","body_content":"...","attachments":[]}`
- `POST /v1/mail/state`
  `{"schema_version":1,"message_ref":"<opaque message_ref>","read":true}`
- Only fall back to deeper contract inspection when one of those routine requests returns a concrete validation or transport error that you need to resolve.

## Binding Checks

- Read [references/env-vars.md](references/env-vars.md) before using the transport.
- Resolve current mailbox bindings through `pixi run python -m houmao.agents.mailbox_runtime_support resolve-live` before direct mailbox work.
- Refuse to use this skill when the resolved `AGENTSYS_MAILBOX_TRANSPORT` is not `stalwart`.
- Re-resolve the current mailbox bindings before each mailbox action. Do not cache session endpoints or credentials across turns.
- Do not scrape tmux state directly or rely on stale inherited process env snapshots when the runtime-owned resolver is available.

## Direct Stalwart Fallback Actions

- Use direct Stalwart access only when no live shared gateway mailbox facade is available or when the task falls outside the shared gateway routine surface.
- Use the current `AGENTSYS_MAILBOX_EMAIL_*` bindings returned by the runtime-owned live resolver for direct Stalwart-backed mailbox access.
- Treat `AGENTSYS_MAILBOX_EMAIL_CREDENTIAL_FILE` as secret material. Read it only when needed for authenticated mailbox access and do not print its contents.
- Use `AGENTSYS_MAILBOX_EMAIL_JMAP_URL` as the JMAP session endpoint.
- Use `AGENTSYS_MAILBOX_EMAIL_LOGIN_IDENTITY` as the mailbox login identity.
- Use `AGENTSYS_MAILBOX_ADDRESS` as the sender address for outbound mail.
- Preserve reply ancestry with standard email headers and the opaque `message_ref` contract.

## Guardrails

- Do not assume filesystem mailbox `rules/`, mailbox-local SQLite, lock files, or projection symlinks exist for this transport.
- Do not leak raw Stalwart object shapes into operator-facing behavior when a shared mailbox operation can stay transport-neutral.
- Do not present direct env-backed transport access as the first-choice attached-session path when the shared gateway facade is available.
