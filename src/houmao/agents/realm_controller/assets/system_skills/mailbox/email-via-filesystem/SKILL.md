---
name: email-via-filesystem
description: Operate the filesystem-backed async mailbox transport for agents using manager-owned live mailbox discovery, the shared gateway mailbox facade when available, and `houmao-mgr agents mail ...` fallback when it is not.
---

# Email Via Filesystem

## Overview

Use this skill when the resolved mailbox transport is `filesystem`.

Treat `houmao-mgr agents mail ...` as the supported discovery and fallback surface for ordinary mailbox work:

1. resolve current bindings through `pixi run houmao-mgr agents mail resolve-live`
2. if `gateway.base_url` is present, use the shared `/v1/mail/*` facade
3. otherwise use `pixi run houmao-mgr agents mail check|send|reply|mark-read`

Do not treat `python -m houmao.agents.mailbox_runtime_support ...` or mailbox-owned scripts as the ordinary workflow contract.

## References

- Read [references/env-vars.md](references/env-vars.md) when validating resolver fields.
- Read [references/filesystem-layout.md](references/filesystem-layout.md) when you need exact mailbox directories, projection layout, or canonical message storage structure.

## Supported Workflow

- Resolve current mailbox bindings through `pixi run houmao-mgr agents mail resolve-live` before mailbox work.
- Treat the resolver output as the supported discovery contract for this turn. Do not scrape tmux state directly.
- When the resolver returns a `gateway` object, use `gateway.base_url` for the live attached `/v1/mail/*` facade.
- When the resolver returns `gateway: null`, use `pixi run houmao-mgr agents mail ...` as the fallback surface.
- Treat `message_ref` and `thread_ref` as opaque shared mailbox references. Do not derive filesystem `message_id`, thread ancestry, or path structure from the visible prefix.
- After you successfully process one nominated unread message, mark that same `message_ref` read through `POST /v1/mail/state` when gateway HTTP is in use or `pixi run houmao-mgr agents mail mark-read --message-ref ...` when it is not.
- If a fallback `houmao-mgr agents mail ...` result returns `authoritative: false`, treat it as submission-only and verify outcome through `pixi run houmao-mgr agents mail check`, `pixi run houmao-mgr agents mail status`, or transport-owned mailbox state before assuming the mutation completed.

## Shared Gateway Route Quick Reference

- `POST /v1/mail/check`
  `{"schema_version":1,"unread_only":true,"limit":10}`
- `POST /v1/mail/send`
  `{"schema_version":1,"to":["recipient@agents.localhost"],"subject":"...","body_content":"...","attachments":[]}`
- `POST /v1/mail/reply`
  `{"schema_version":1,"message_ref":"<opaque message_ref>","body_content":"...","attachments":[]}`
- `POST /v1/mail/state`
  `{"schema_version":1,"message_ref":"<opaque message_ref>","read":true}`

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
