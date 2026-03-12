# Filesystem Mailbox

`gig_agents` provides a runtime-owned async mailbox surface for mailbox-enabled sessions. In v1, the only implemented mailbox transport is `filesystem`.

Use this page together with [Brain Launch Runtime](brain_launch_runtime.md) when you need the operator-facing session workflow plus the mailbox transport details.

## Enable Mailbox Support

Mailbox support can come from declarative recipe or manifest config or from `start-session` overrides.

Declarative mailbox fields:

- `transport`
- `principal_id`
- `address`
- `filesystem_root`

Example runtime override:

```bash
pixi run python -m gig_agents.agents.brain_launch_runtime start-session \
  --agent-def-dir tests/fixtures/agents \
  --brain-manifest tmp/agents-runtime/manifests/claude/<home-id>.yaml \
  --role gpu-kernel-coder \
  --backend claude_headless \
  --mailbox-transport filesystem \
  --mailbox-root tmp/shared-mail \
  --mailbox-principal-id AGENTSYS-research \
  --mailbox-address AGENTSYS-research@agents.localhost
```

When mailbox support is enabled, the runtime bootstraps or validates the mailbox root, safely registers the session mailbox, projects the runtime-owned skill `.system/mailbox/email-via-filesystem`, and persists the resolved mailbox binding in the session manifest so resumed sessions keep using the same mailbox configuration.

## Canonical Mailbox Model

Canonical mailbox messages are transport-neutral envelopes with immutable delivered content and mutable per-recipient mailbox state stored separately.

The canonical envelope includes at minimum:

- `message_id`
- `thread_id`
- `created_at_utc`
- sender principal
- recipient principals
- `subject`
- `body_markdown`
- attachment metadata
- extensible headers

Important v1 semantics:

- `message_id` uses `msg-{YYYYMMDDTHHMMSSZ}-{uuid4-no-dashes}`.
- Root messages use their own `message_id` as `thread_id`.
- Replies carry explicit `in_reply_to` and `references`; subject changes alone do not create a new thread.
- Participants are addressed by stable mailbox principal plus full mailbox address such as `AGENTSYS-research@agents.localhost`.
- Read or unread and related mailbox state live in SQLite and do not rewrite the canonical Markdown message body.

## Runtime Mail Commands

Use the runtime `mail` subcommands against a resumed mailbox-enabled session:

```bash
pixi run python -m gig_agents.agents.brain_launch_runtime mail check \
  --agent-identity AGENTSYS-research \
  --unread-only \
  --limit 10

pixi run python -m gig_agents.agents.brain_launch_runtime mail send \
  --agent-identity AGENTSYS-research \
  --to AGENTSYS-orchestrator@agents.localhost \
  --subject "Investigate parser drift" \
  --body-file body.md \
  --attach notes.txt

pixi run python -m gig_agents.agents.brain_launch_runtime mail reply \
  --agent-identity AGENTSYS-research \
  --message-id msg-20260312T050000Z-parent \
  --body-content "Reply with next steps"
```

Command rules:

- `mail check` supports `--unread-only`, `--limit`, and `--since`.
- `mail send` requires at least one `--to`, a `--subject`, and explicit body content via `--body-file` or `--body-content`.
- `mail reply` requires `--message-id` and explicit body content via `--body-file` or `--body-content`.
- `mail send` and `mail reply` accept repeatable `--attach` file paths.
- Recipient arguments must use full mailbox addresses, not short agent names.

The runtime owns the prompt and result envelope for these commands. Operators call the CLI and receive structured JSON on stdout; the session itself is prompted to use the projected mailbox system skill and return one mailbox result payload.

## Runtime Mailbox Bindings

Mailbox-enabled sessions receive stable env bindings instead of hardcoded mailbox paths in skill text.

Common bindings:

- `AGENTSYS_MAILBOX_TRANSPORT`
- `AGENTSYS_MAILBOX_PRINCIPAL_ID`
- `AGENTSYS_MAILBOX_ADDRESS`
- `AGENTSYS_MAILBOX_BINDINGS_VERSION`

Filesystem-specific bindings:

- `AGENTSYS_MAILBOX_FS_ROOT`
- `AGENTSYS_MAILBOX_FS_SQLITE_PATH`
- `AGENTSYS_MAILBOX_FS_INBOX_DIR`

Binding rules:

- Re-read mailbox bindings before each mailbox action.
- Treat `AGENTSYS_MAILBOX_FS_ROOT` as authoritative instead of reconstructing mailbox paths from the runtime root.
- `AGENTSYS_MAILBOX_FS_INBOX_DIR` follows the active mailbox registration path for `AGENTSYS_MAILBOX_ADDRESS`, so it may resolve through a symlinked `mailboxes/<address>` entry into a private mailbox directory outside the shared root.
- If `AGENTSYS_MAILBOX_BINDINGS_VERSION` changes, discard cached mailbox assumptions and reload the current bindings.

## Filesystem Layout

The effective mailbox root defaults to `<runtime_root>/mailbox` when no explicit override is configured.

Core layout:

```text
<mailbox_root>/
  protocol-version.txt
  index.sqlite
  rules/
    README.md
    protocols/filesystem-mailbox-v1.md
    scripts/
      requirements.txt
      register_mailbox.py
      deregister_mailbox.py
      deliver_message.py
      insert_standard_headers.py
      update_mailbox_state.py
      repair_index.py
  locks/
    index.lock
    addresses/<address>.lock
  messages/YYYY-MM-DD/<message-id>.md
  attachments/managed/<attachment-id>/
  mailboxes/<address>/
    inbox/
    sent/
    archive/
    drafts/
  staging/
```

Layout rules:

- Canonical delivered messages are Markdown files under `messages/<YYYY-MM-DD>/`.
- `mailboxes/<address>/inbox` and `mailboxes/<address>/sent` hold symlink projections back to the canonical message file.
- `mailboxes/<address>` may be a real directory under the shared root or a symlink to a private mailbox directory.
- `archive/` and `drafts/` are reserved placeholder directories in v1.
- The SQLite index stays in a non-WAL journal mode in v1.
- Stale roots from the earlier principal-keyed layout are unsupported; delete and re-bootstrap them instead of migrating in place.

## Shared Rules And Managed Helpers

Always inspect the mailbox-local `rules/` tree before touching shared mailbox state. The shared root publishes the human-readable README, the filesystem mailbox protocol note, helper skills, and the managed scripts for sensitive operations.

Managed helper contract:

- Python helpers declare their dependencies in `rules/scripts/requirements.txt`.
- Managed helpers keep the stable `--mailbox-root` plus `--payload-file` CLI contract.
- Managed helpers emit exactly one JSON object to stdout for both success and failure cases.
- Delivery, mailbox-state mutation, repair, register, and deregister flows validate payloads through strict shared `pydantic` schemas before mutating mailbox files or SQLite state.
- Validation failures report structured field-aware JSON errors instead of partially mutating the mailbox.

If a mailbox claims to be initialized but the managed `rules/scripts/` assets are missing, treat that as a mailbox bootstrap problem rather than improvising replacement scripts.

## Registration Lifecycle

Filesystem mailbox registration is address-routed and keyed by the full mailbox address. At most one `active` registration exists for a given address at a time.

Join modes:

- `safe`: default; reuse a matching active registration and fail on real conflicts.
- `force`: replace the active registration for that address.
- `stash`: preserve the previous mailbox artifact with a UUID4 suffix, mark it `stashed`, and create a fresh active registration.

Leave modes:

- `deactivate`: default; stop future delivery while preserving historical state.
- `purge`: remove registration-scoped mutable state and shared-root registration artifacts without deleting canonical messages under `messages/`.

All delivery, registration, deregistration, mailbox-state mutation, and repair flows serialize on `locks/addresses/<address>.lock` before taking `locks/index.lock`.

## Future Email Compatibility

The canonical mailbox protocol keeps `message_id`, `in_reply_to`, `references`, sender and recipient identities, subject, thread identity, Markdown body semantics, and attachment metadata compatible with a future true-email transport.

This repository does not yet implement SMTP, IMAP, localhost mail services, or live switching between filesystem and future email transports within one session.
