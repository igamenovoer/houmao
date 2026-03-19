---
name: email-via-stalwart
description: Operate the Stalwart-backed mailbox transport for agents using runtime-provided email mailbox env vars and the live gateway mailbox facade when available.
license: MIT
---

Use this skill when the runtime-selected mailbox transport is `stalwart`.

Key rules:

- Read [references/env-vars.md](references/env-vars.md) before using the transport.
- Prefer the live gateway mailbox facade exposed through the existing gateway env bindings and `/v1/mail/*` routes for shared mailbox operations: `check`, `send`, and `reply`.
- When no live gateway mailbox facade is available, use the runtime-managed `AGENTSYS_MAILBOX_EMAIL_*` env vars for direct Stalwart-backed mailbox access.
- Treat `AGENTSYS_MAILBOX_EMAIL_CREDENTIAL_FILE` as secret material. Read it only when needed for authenticated mailbox access and do not print its contents.
- Do not assume filesystem mailbox `rules/`, mailbox-local SQLite, lock files, or projection symlinks exist for this transport.
- Keep shared mailbox behavior transport-neutral: return opaque `message_ref` values, preserve reply ancestry, and do not leak raw Stalwart object shapes into the operator-facing result.

When using direct Stalwart access:

1. Use `AGENTSYS_MAILBOX_EMAIL_JMAP_URL` as the JMAP session endpoint.
2. Use `AGENTSYS_MAILBOX_EMAIL_LOGIN_IDENTITY` as the mailbox login identity.
3. Resolve credentials through `AGENTSYS_MAILBOX_EMAIL_CREDENTIAL_FILE`.
4. Use `AGENTSYS_MAILBOX_ADDRESS` as the sender address for outbound mail.
5. Preserve reply ancestry with standard email headers and the opaque `message_ref` contract.
