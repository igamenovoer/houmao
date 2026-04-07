# Filesystem Transport Guidance

Use this page when the resolved mailbox transport is `filesystem`.

For notifier-driven shared mailbox gateway work, use `houmao-process-emails-via-gateway`.

For shared gateway mailbox actions in ordinary mailbox work, stay on this skill's action pages and use the exact `gateway.base_url` returned by the resolver or already present in prompt or context.

Use this filesystem page for:

- validating that the resolved transport is `filesystem`,
- understanding filesystem mailbox layout and local policy guidance,
- deciding how to fall back when `gateway: null`,
- transport-specific read-state verification or inspection.

## Filesystem Workflow

- When the current prompt or mailbox context already provides the exact `gateway.base_url`, use that value directly for shared gateway mailbox work and do not rerun manager discovery first.
- Otherwise resolve current mailbox bindings through `houmao-mgr agents mail resolve-live` before mailbox work.
- Treat the resolver output as the supported discovery contract for this turn. Do not scrape tmux state directly.
- When the resolver returns a `gateway` object, use this skill's action pages and shared `/v1/mail/*` references for the ordinary mailbox operation you need.
- When the resolver returns `gateway: null`, use `houmao-mgr agents mail status|check|send|reply|mark-read` as the supported fallback surface.
- Treat `message_ref` and `thread_ref` as opaque shared mailbox references. Do not derive filesystem `message_id`, thread ancestry, or path structure from the visible prefix.
- After you successfully process one message, mark that same `message_ref` read through `POST /v1/mail/state` when gateway HTTP is in use or `houmao-mgr agents mail mark-read --message-ref ...` when it is not.
- If a fallback `houmao-mgr agents mail ...` result returns `authoritative: false`, treat it as submission-only and verify outcome through `houmao-mgr agents mail check`, `houmao-mgr agents mail status`, or transport-owned mailbox state before assuming the mutation completed.

## Filesystem-Specific Guidance

- Read [../references/filesystem-resolver-fields.md](../references/filesystem-resolver-fields.md) when validating resolver fields.
- Read [../references/filesystem-layout.md](../references/filesystem-layout.md) when you need exact mailbox directories, projection layout, or canonical message storage structure.
- Inspect the shared mailbox `rules/` directory under `mailbox.filesystem.root` for mailbox-local policy guidance such as formatting, etiquette, or workflow hints.
- Treat that `rules/` content as policy guidance, not as the ordinary public execution protocol.
- `rules/scripts/`, when present, is compatibility or implementation detail. Do not treat shared helper scripts as the first-choice surface for ordinary `check`, `send`, `reply`, or `mark-read` work.
- Inspect unread state from `mailbox.filesystem.local_sqlite_path` when transport-owned inspection is needed; treat that mailbox-local database as the source of truth for read or unread, starred, archived, deleted, and thread summary state for the current mailbox.
- Treat `mailbox.filesystem.sqlite_path` as shared structural catalog state, not as the mailbox-view authority for the current mailbox.
- Read message content by following inbox or sent symlink projections back to canonical Markdown message files under `messages/<YYYY-MM-DD>/...`.

## Guardrails

- Refuse to use this page when `mailbox.transport` is not `filesystem`.
- Do not hardcode mailbox roots, SQLite paths, or mailbox addresses into instructions, prompts, or generated files.
- Do not assume mailbox content lives under the runtime root unless the resolved bindings explicitly point there.
- Do not invent archive or draft folder workflows in v1; treat `archive/` and `drafts/` as reserved placeholders unless a future change defines those workflows.
- Do not rewrite delivered Markdown messages to mark them read, starred, or archived.
- Do not bypass locking when creating or updating mailbox projections.
