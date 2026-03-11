---
name: email-via-filesystem
description: Operate the filesystem-backed async mailbox transport for agents using runtime-provided mailbox env vars. Use when Codex needs to read, send, reply to, or inspect email-like messages stored as Markdown files under a runtime-provided mailbox content root with SQLite-backed mailbox state and lock-file synchronization.
---

# Email Via Filesystem

## Overview

Use this skill to work with the mailbox transport where messages live on the local filesystem as Markdown files and mailbox state lives in SQLite. Treat this as the system-defined mailbox skill for the `filesystem` transport, not as a role-authored workflow. Do not assume mailbox content lives under the run directory; use the env-provided filesystem mailbox root.

## References

- Read [references/env-vars.md](references/env-vars.md) when validating mailbox bindings.
- Read [references/filesystem-layout.md](references/filesystem-layout.md) when you need exact mailbox directories, projection layout, or canonical message storage structure.

## Binding Checks

- Require the common and filesystem-specific env vars defined in [references/env-vars.md](references/env-vars.md).
- Refuse to use this skill when `AGENTSYS_MAILBOX_TRANSPORT` is not `filesystem`.
- Re-read the mailbox env vars before each mailbox action. Do not cache paths or addresses across turns.

## Read Mail

- Inspect unread state from SQLite when available; treat the database as the source for read or unread, starred, archived, and thread summary state.
- Read message content from the Markdown mailbox corpus, not from ad hoc cached copies.
- Use [references/filesystem-layout.md](references/filesystem-layout.md) for the exact mailbox tree and message file shape.
- Preserve thread ancestry exactly as stored. Do not infer thread membership from subject lines alone.
- If `AGENTSYS_MAILBOX_BINDINGS_VERSION` changes mid-task, discard cached mailbox assumptions and reload the current bindings before continuing.

## Send Or Reply

- Use a new `message_id` for each outgoing message.
- For a new thread, set `thread_id = message_id`.
- For a reply, preserve the existing `thread_id`, set `in_reply_to` to the direct parent, and extend `references`.
- Keep message bodies in Markdown.
- Keep attachments as structured references unless the runtime explicitly indicates managed-copy storage.
- Use the env-provided mailbox principal and address values rather than hardcoding sender identity or transport paths.

When writing directly to the filesystem transport:

1. Stage the outgoing message before exposing it to recipients.
2. Respect the mailbox `.lock` files for any principal whose mailbox state or projections will be changed.
3. Keep canonical message content immutable after delivery.
4. Update mutable mailbox state in SQLite instead of rewriting delivered message bodies.

## Guardrails

- Do not hardcode mailbox roots, SQLite paths, or mailbox addresses into instructions, prompts, or generated files.
- Do not assume mailbox content lives under the runtime root unless the env bindings explicitly point there.
- Do not treat mailbox filenames alone as unread or read markers.
- Do not rewrite delivered Markdown messages to mark them read, starred, or archived.
- Do not bypass locking when creating or updating mailbox projections.
- Do not assume a true-email runtime transport exists in this change; if the transport is not `filesystem`, stop and report that only the filesystem mailbox transport is implemented here. Use `$email-via-mail-system` only for compatibility guidance.
