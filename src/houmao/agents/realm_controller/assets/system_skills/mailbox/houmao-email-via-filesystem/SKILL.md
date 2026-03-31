---
name: houmao-email-via-filesystem
description: Use Houmao's filesystem mailbox transport guidance for transport-specific validation, layout, and no-gateway fallback while delegating shared gateway mailbox operations to `houmao-email-via-agent-gateway`.
---

# Houmao Email Via Filesystem

## Overview

Use this Houmao skill when the resolved mailbox transport is `filesystem`.

For shared mailbox gateway work, use the installed Houmao gateway skill `houmao-email-via-agent-gateway`.

Use this transport-specific skill for:
- validating that the resolved transport is `filesystem`,
- understanding filesystem mailbox layout and local policy guidance,
- deciding how to fall back when `gateway: null`,
- transport-specific read-state verification or inspection.

Use the manager-owned discovery command `pixi run houmao-mgr agents mail resolve-live` before mailbox work.

## References

- Read [references/env-vars.md](references/env-vars.md) when validating resolver fields.
- Read [references/filesystem-layout.md](references/filesystem-layout.md) when you need exact mailbox directories, projection layout, or canonical message storage structure.
- Read `skills/mailbox/houmao-email-via-agent-gateway/SKILL.md` when `gateway.base_url` is present and the task is ordinary shared mailbox work.

## Supported Workflow

- Resolve current mailbox bindings through `pixi run houmao-mgr agents mail resolve-live` before mailbox work.
- Treat the resolver output as the supported discovery contract for this turn. Do not scrape tmux state directly.
- When the resolver returns a `gateway` object, use the installed Houmao skill `houmao-email-via-agent-gateway` for the live attached `/v1/mail/*` facade.
- When the resolver returns `gateway: null`, use `pixi run houmao-mgr agents mail ...` as the fallback surface.
- Treat `message_ref` and `thread_ref` as opaque shared mailbox references. Do not derive filesystem `message_id`, thread ancestry, or path structure from the visible prefix.
- After you successfully process one message, mark that same `message_ref` read through `POST /v1/mail/state` when gateway HTTP is in use or `pixi run houmao-mgr agents mail mark-read --message-ref ...` when it is not.
- If a fallback `houmao-mgr agents mail ...` result returns `authoritative: false`, treat it as submission-only and verify outcome through `pixi run houmao-mgr agents mail check`, `pixi run houmao-mgr agents mail status`, or transport-owned mailbox state before assuming the mutation completed.

## Binding Checks

- Require the common and filesystem-specific resolver fields defined in [references/env-vars.md](references/env-vars.md).
- When the resolver returns `gateway.base_url`, treat that value as the exact live shared-mailbox endpoint instead of guessing another loopback URL.
- Refuse to use this skill when `mailbox.transport` is not `filesystem`.
- Do not cache paths or addresses across turns. Re-resolve the current mailbox bindings before each mailbox action that needs fresh transport state.
- If `bindings_version` changes mid-task, discard cached mailbox assumptions and resolve the current bindings again before continuing.

## Filesystem-Specific Guidance

- Inspect the shared mailbox `rules/` directory under `mailbox.filesystem.root` for mailbox-local policy guidance such as formatting, etiquette, or workflow hints.
- Treat that `rules/` content as policy guidance, not as the ordinary public execution protocol.
- `rules/scripts/`, when present, is compatibility or implementation detail. Do not treat shared helper scripts as the first-choice surface for ordinary `check`, `send`, `reply`, or `mark-read` work.
- Inspect unread state from `mailbox.filesystem.local_sqlite_path` when transport-owned inspection is needed; treat that mailbox-local database as the source of truth for read or unread, starred, archived, deleted, and thread summary state for the current mailbox.
- Treat `mailbox.filesystem.sqlite_path` as shared structural catalog state, not as the mailbox-view authority for the current mailbox.
- Read message content by following inbox or sent symlink projections back to canonical Markdown message files under `messages/<YYYY-MM-DD>/...`.

## Guardrails

- Do not hardcode mailbox roots, SQLite paths, or mailbox addresses into instructions, prompts, or generated files.
- Do not assume mailbox content lives under the runtime root unless the resolved bindings explicitly point there.
- Do not invent archive or draft folder workflows in v1; treat `archive/` and `drafts/` as reserved placeholders unless a future change defines those workflows.
- Do not treat mailbox filenames alone as unread or read markers.
- Do not rewrite delivered Markdown messages to mark them read, starred, or archived.
- Do not mark a message read merely because unread mail was detected or because a reminder prompt mentioned it.
- Do not bypass locking when creating or updating mailbox projections.
- Do not copy delivered canonical message bodies into `inbox/` or `sent/`; those mailbox entries should be symlink projections to the canonical file.
- Do not present `deliver_message.py` or `update_mailbox_state.py` as the ordinary workflow contract for this skill.
- Do not restate the shared gateway curl contract here; use `houmao-email-via-agent-gateway` for that operational surface.
