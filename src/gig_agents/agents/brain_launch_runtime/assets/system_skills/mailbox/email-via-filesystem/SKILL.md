---
name: email-via-filesystem
description: Operate the filesystem-backed async mailbox transport for agents using runtime-provided mailbox env vars. Use when Codex needs to read, send, reply to, or inspect email-like messages stored as Markdown files under a runtime-provided mailbox content root with SQLite-backed mailbox state and lock-file synchronization.
---

# Email Via Filesystem

## Overview

Use this skill to work with the mailbox transport where canonical messages live on the local filesystem as Markdown files under `messages/<YYYY-MM-DD>/...`, mailbox-visible inbox or sent entries are symlink projections to those canonical files, and mailbox state lives in SQLite. Treat this as the system-defined mailbox skill for the `filesystem` transport, not as a role-authored workflow. Do not assume mailbox content lives under the run directory; use the env-provided filesystem mailbox root.

## References

- Read [references/env-vars.md](references/env-vars.md) when validating mailbox bindings.
- Read [references/filesystem-layout.md](references/filesystem-layout.md) when you need exact mailbox directories, projection layout, or canonical message storage structure.

## Binding Checks

- Require the common and filesystem-specific env vars defined in [references/env-vars.md](references/env-vars.md).
- Refuse to use this skill when `AGENTSYS_MAILBOX_TRANSPORT` is not `filesystem`.
- Re-read the mailbox env vars before each mailbox action. Do not cache paths or addresses across turns.
- Before interacting with shared mailbox state, inspect the shared mailbox `rules/` directory under `AGENTSYS_MAILBOX_FS_ROOT` and follow any mailbox-local README, scripts, or helper skills there.
- If the mailbox claims to be initialized but the managed `rules/scripts/` files are missing, stop and report a mailbox-initialization error instead of improvising replacements.
- Before invoking a shared Python helper from `rules/scripts/`, inspect `rules/scripts/requirements.txt` so you know which Python dependencies must already be installed or need to be installed for that mailbox.
- For any mailbox step that touches `index.sqlite` or `locks/`, use the shared helper script from `rules/scripts/` when the shared mailbox provides one.
- When the shared mailbox provides a header-helper script under `rules/scripts/`, you may use it to insert or normalize standardized headers or YAML front matter during message composition, but treat it as optional guidance rather than a required transport primitive.

## Read Mail

- Inspect the shared mailbox `rules/` directory first so mailbox-local rules can refine how this particular shared mailbox expects reads or status updates to work.
- Inspect unread state from SQLite when available; treat the database as the source for read or unread, starred, archived, and thread summary state.
- Read message content by following inbox or sent symlink projections back to the canonical Markdown message file in `messages/<YYYY-MM-DD>/...`, not from ad hoc cached copies.
- Use [references/filesystem-layout.md](references/filesystem-layout.md) for the exact mailbox tree and message file shape.
- Preserve thread ancestry exactly as stored. Do not infer thread membership from subject lines alone.
- If `AGENTSYS_MAILBOX_BINDINGS_VERSION` changes mid-task, discard cached mailbox assumptions and reload the current bindings before continuing.

## Send Or Reply

- Inspect the shared mailbox `rules/` directory first so mailbox-local rules, scripts, or helper skills can refine standardized mailbox operations for this shared mail group.
- Use a new `message_id` for each outgoing message.
- Generate `message_id` using the format `msg-{YYYYMMDDTHHMMSSZ}-{uuid4-no-dashes}`.
- For a new thread, set `thread_id = message_id`.
- For a reply, preserve the existing `thread_id`, set `in_reply_to` to the direct parent, and extend `references`.
- Keep message bodies in Markdown.
- Keep attachments as structured references unless the runtime explicitly indicates managed-copy storage.
- Use the env-provided mailbox principal and address values rather than hardcoding sender identity or transport paths.

When writing directly to the filesystem transport:

1. Stage the outgoing message before exposing it to recipients.
2. Inspect `rules/scripts/requirements.txt` before invoking a shared Python helper from `rules/scripts/`.
3. Use the shared helper script from `rules/scripts/` for sensitive steps that touch `index.sqlite` or `locks/`.
4. Respect the mailbox `.lock` files for any full mailbox address whose registration, mailbox state, or projections will be changed.
5. Place the canonical delivered Markdown message under `messages/<YYYY-MM-DD>/...`.
6. Materialize recipient inbox and sender sent entries as symlink projections to that canonical message instead of copying the message body into mailbox folders.
7. Keep canonical message content immutable after delivery.
8. Update mutable mailbox state in SQLite instead of rewriting delivered message bodies.

## Guardrails

- Do not hardcode mailbox roots, SQLite paths, or mailbox addresses into instructions, prompts, or generated files.
- Do not assume mailbox content lives under the runtime root unless the env bindings explicitly point there.
- Do not skip the shared mailbox `rules/` directory when interacting with a shared mail root; mailbox-local rules there are the first place to look for standardized operation guidance.
- Do not hand-write raw SQLite mutations or lock-file orchestration when the shared mailbox provides a standardized helper script for that sensitive operation under `rules/scripts/`.
- Do not assume shared Python helper dependencies are already available without checking `rules/scripts/requirements.txt`.
- Do not invent archive or draft folder workflows in v1; treat `archive/` and `drafts/` as reserved placeholders unless a future change defines those workflows.
- Do not treat mailbox filenames alone as unread or read markers.
- Do not rewrite delivered Markdown messages to mark them read, starred, or archived.
- Do not bypass locking when creating or updating mailbox projections.
- Do not copy delivered canonical message bodies into `inbox/` or `sent/`; those mailbox entries should be symlink projections to the canonical file.
- Do not assume a true-email runtime transport exists in this change; if the transport is not `filesystem`, stop and report that only the filesystem mailbox transport is implemented here.
