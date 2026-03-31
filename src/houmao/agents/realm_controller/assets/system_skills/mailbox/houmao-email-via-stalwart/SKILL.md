---
name: houmao-email-via-stalwart
description: Use Houmao's Stalwart mailbox transport guidance for transport-specific validation and fallback while delegating shared gateway mailbox operations to `houmao-email-via-agent-gateway`.
license: MIT
---

# Houmao Email Via Stalwart

Use this Houmao skill when the resolved mailbox transport is `stalwart`.

## Supported Workflow

- Resolve current mailbox bindings through `pixi run houmao-mgr agents mail resolve-live` before mailbox work.
- Treat that resolver output as the manager-owned discovery contract for this turn.
- When the resolver returns a `gateway` object, use the installed Houmao skill `houmao-email-via-agent-gateway` for the live attached `/v1/mail/*` facade.
- When the resolver returns `gateway: null`, use `pixi run houmao-mgr agents mail check|send|reply|mark-read` as the fallback surface.
- Ordinary mailbox work in this change means `check`, `send`, `reply`, and marking one processed message read.
- Treat `message_ref` and `thread_ref` as opaque shared mailbox references. Do not derive raw Stalwart object identifiers or transport-local structure from the visible prefix.
- After you successfully process one message, mark that same `message_ref` read through `POST /v1/mail/state` when gateway HTTP is in use or `pixi run houmao-mgr agents mail mark-read --message-ref ...` when it is not.
- If a fallback `houmao-mgr agents mail ...` result returns `authoritative: false`, treat it as submission-only and verify outcome through `pixi run houmao-mgr agents mail check`, `pixi run houmao-mgr agents mail status`, or transport-native mailbox state before assuming the mutation completed.

## Binding Checks

- Read [references/env-vars.md](references/env-vars.md) before using the transport.
- When the resolver returns a `gateway` object, treat `gateway.base_url` as the exact live endpoint for the shared `/v1/mail/*` facade instead of rediscovering host or port elsewhere.
- Refuse to use this skill when `mailbox.transport` is not `stalwart`.
- Re-resolve the current mailbox bindings before each mailbox action. Do not cache session endpoints or credentials across turns.
- Do not scrape tmux state directly or rely on stale inherited process env snapshots when the manager-owned resolver is available.

## Direct Stalwart Guidance

- Use direct Stalwart access only when no live shared gateway mailbox facade is available or when the task falls outside the shared gateway routine surface.
- Use the current `mailbox.stalwart.*` fields returned by the resolver for direct Stalwart-backed mailbox access.
- Treat `mailbox.stalwart.credential_file` as secret material. Read it only when needed for authenticated mailbox access and do not print its contents.
- Use `address` as the sender address for outbound mail.
- Preserve reply ancestry with standard email headers and the opaque `message_ref` contract.

## Guardrails

- Do not assume filesystem mailbox `rules/`, mailbox-local SQLite, lock files, or projection symlinks exist for this transport.
- Do not leak raw Stalwart object shapes into operator-facing behavior when a shared mailbox operation can stay transport-neutral.
- Do not present direct env-backed transport access as the first-choice attached-session path when the shared gateway facade is available.
- Do not restate the shared gateway curl contract here; use `houmao-email-via-agent-gateway` for that operational surface.
