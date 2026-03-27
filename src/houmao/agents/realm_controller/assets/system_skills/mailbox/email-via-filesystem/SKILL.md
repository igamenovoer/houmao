---
name: email-via-filesystem
description: Operate the filesystem-backed async mailbox transport for agents using runtime-provided mailbox env vars. Use when Codex needs to read, send, reply to, or inspect email-like messages stored as Markdown files under a runtime-provided mailbox content root with a shared SQLite catalog, mailbox-local SQLite state, and lock-file synchronization.
---

# Email Via Filesystem

## Overview

Use this skill to work with the filesystem mailbox transport where canonical messages live on the local filesystem under `messages/<YYYY-MM-DD>/...`, mailbox-visible inbox or sent entries are symlink projections to those canonical files, shared catalog state lives in `index.sqlite`, and mailbox-view state for the current mailbox lives in mailbox-local `mailbox.sqlite`. Treat this as the system-defined mailbox skill for the `filesystem` transport, not as a role-authored workflow. Do not assume mailbox content lives under the run directory; use the env-provided filesystem mailbox root.

## References

- Read [references/env-vars.md](references/env-vars.md) when validating mailbox bindings.
- Read [references/filesystem-layout.md](references/filesystem-layout.md) when you need exact mailbox directories, projection layout, or canonical message storage structure.

## Routine Actions With A Live Gateway Facade

- Resolve current mailbox bindings through `pixi run python -m houmao.agents.mailbox_runtime_support resolve-live` before attached shared-mailbox work.
- Treat the resolver output as the runtime-owned discovery contract for this turn: use `gateway.base_url` for the live attached `/v1/mail/*` facade when that `gateway` object is present.
- That resolver prefers current process env, falls back to the owning tmux session env, and returns `gateway: null` instead of guessing a localhost endpoint when no valid live gateway is available.
- When a live loopback gateway exposes the shared `/v1/mail/*` facade for this session, treat that gateway surface as the default routine path for ordinary mailbox work.
- Ordinary attached-session mailbox work in this change means `check`, `send`, `reply`, and marking one processed message read.
- Prefer the shared gateway mailbox routes for those routine actions: `POST /v1/mail/check`, `POST /v1/mail/send`, `POST /v1/mail/reply`, and `POST /v1/mail/state`.
- Treat `message_ref` and `thread_ref` as opaque shared mailbox references. Do not derive filesystem `message_id`, thread ancestry, or path structure from the visible prefix.
- After you successfully process one nominated unread message, mark that same `message_ref` read through `POST /v1/mail/state` with `read=true`.
- Do not reconstruct `deliver_message.py`, `update_mailbox_state.py`, raw threading payloads, or ad hoc SQLite mutations for ordinary attached-session turns when the shared gateway facade is available.

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

- Resolve current mailbox bindings through `pixi run python -m houmao.agents.mailbox_runtime_support resolve-live` before direct mailbox work.
- Require the common and filesystem-specific mailbox binding keys defined in [references/env-vars.md](references/env-vars.md) from that resolver output.
- When the resolver returns a `gateway` object, treat `gateway.base_url` as the exact live endpoint for the shared `/v1/mail/*` facade instead of re-discovering host or port through docs, tmux scraping, or localhost guesses.
- Refuse to use this skill when the resolved `AGENTSYS_MAILBOX_TRANSPORT` is not `filesystem`.
- Do not cache paths or addresses across turns. Re-resolve the current mailbox bindings before each mailbox action that uses direct filesystem access.
- If `AGENTSYS_MAILBOX_BINDINGS_VERSION` changes mid-task, discard cached mailbox assumptions and resolve the current bindings again before continuing.
- Do not scrape tmux state directly or rely on stale inherited process env snapshots when the runtime-owned resolver is available.

## Direct Filesystem Fallback Actions

- Use the direct filesystem transport path only when no live shared gateway mailbox facade is available or when the task falls outside the shared gateway routine surface.
- Before interacting with shared mailbox state through direct filesystem access, inspect the shared mailbox `rules/` directory under `AGENTSYS_MAILBOX_FS_ROOT` and follow any mailbox-local README, scripts, or helper skills there.
- If the mailbox claims to be initialized but the managed `rules/scripts/` files are missing, stop and report a mailbox-initialization error instead of improvising replacements.
- Before invoking a shared Python helper from `rules/scripts/`, inspect `rules/scripts/requirements.txt` so you know which dependencies the mailbox expects.
- For any direct filesystem step that touches shared `index.sqlite`, mailbox-local `mailbox.sqlite`, or `locks/`, use the shared helper script from `rules/scripts/` when the shared mailbox provides one.

## Direct Read Mail

- Inspect unread state from `AGENTSYS_MAILBOX_FS_LOCAL_SQLITE_PATH` when available; treat that mailbox-local database as the source of truth for read or unread, starred, archived, deleted, and thread summary state for the current mailbox.
- Treat `AGENTSYS_MAILBOX_FS_SQLITE_PATH` as shared structural catalog state, not as the mailbox-view authority for the current mailbox.
- Read message content by following inbox or sent symlink projections back to the canonical Markdown message file in `messages/<YYYY-MM-DD>/...`, not from ad hoc cached copies.
- Preserve thread ancestry exactly as stored. Do not infer thread membership from subject lines alone.
- Mark a message read only after the message has actually been processed successfully.

## Direct Send Or Reply

- Use a new `message_id` for each outgoing message.
- Generate `message_id` using the format `msg-{YYYYMMDDTHHMMSSZ}-{uuid4-no-dashes}`.
- For a new thread, set `thread_id = message_id`.
- For a reply, preserve the existing `thread_id`, set `in_reply_to` to the direct parent, and extend `references`.
- Keep message bodies in Markdown.
- Keep attachments as structured references unless the runtime explicitly indicates managed-copy storage.
- Use the env-provided mailbox principal and address values rather than hardcoding sender identity or transport paths.

When writing directly to the filesystem transport:

1. Stage the outgoing message before exposing it to recipients.
2. Use the shared helper script from `rules/scripts/` for sensitive steps that touch shared `index.sqlite`, mailbox-local `mailbox.sqlite`, or `locks/`.
3. Respect the mailbox `.lock` files for any full mailbox address whose registration, mailbox state, or projections will be changed.
4. Place the canonical delivered Markdown message under `messages/<YYYY-MM-DD>/...`.
5. Materialize recipient inbox and sender sent entries as symlink projections to that canonical message instead of copying the message body into mailbox folders.
6. Keep canonical message content immutable after delivery.
7. Update mailbox-view state in mailbox-local SQLite instead of rewriting delivered message bodies.

## Guardrails

- Do not hardcode mailbox roots, SQLite paths, or mailbox addresses into instructions, prompts, or generated files.
- Do not assume mailbox content lives under the runtime root unless the env bindings explicitly point there.
- Do not skip the shared mailbox `rules/` directory when direct filesystem access is required.
- Do not hand-write raw SQLite mutations or lock-file orchestration when the shared mailbox provides a standardized helper script for that sensitive operation under `rules/scripts/`.
- Do not assume shared Python helper dependencies are already available without checking `rules/scripts/requirements.txt`.
- Do not invent archive or draft folder workflows in v1; treat `archive/` and `drafts/` as reserved placeholders unless a future change defines those workflows.
- Do not treat mailbox filenames alone as unread or read markers.
- Do not rewrite delivered Markdown messages to mark them read, starred, or archived.
- Do not mark a message read merely because unread mail was detected or because a reminder prompt mentioned it.
- Do not bypass locking when creating or updating mailbox projections.
- Do not copy delivered canonical message bodies into `inbox/` or `sent/`; those mailbox entries should be symlink projections to the canonical file.
- Do not present `deliver_message.py` or `update_mailbox_state.py` as the first-choice attached-session path when the shared gateway facade is available.
