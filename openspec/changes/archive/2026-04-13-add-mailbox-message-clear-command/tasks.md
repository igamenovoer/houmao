## 1. Core Mailbox Behavior

- [x] 1.1 Add mailbox-managed result/action modeling for clearing delivered messages while preserving registration state.
- [x] 1.2 Implement the locked `clear_mailbox_messages` helper in the filesystem mailbox managed layer with dry-run and apply modes.
- [x] 1.3 Remove canonical message files, recorded projection artifacts, shared message/index rows, shared thread summaries, mailbox-local message/thread state, and mailbox-owned managed-copy attachments in apply mode.
- [x] 1.4 Preserve active, inactive, and stashed registration rows, mailbox account directories, symlinked private mailbox targets, root protocol/rules/locks/staging layout, and external `path_ref` attachment targets.
- [x] 1.5 Make the clear operation idempotent and report blocked filesystem or SQLite actions without unregistering accounts.

## 2. CLI Plumbing

- [x] 2.1 Add a shared command helper in `mailbox_support.py` that exposes the managed clear operation with structured cleanup-style payloads.
- [x] 2.2 Add `houmao-mgr mailbox clear-messages [--mailbox-root <path>] [--dry-run] [--yes]` with interactive confirmation and non-interactive failure behavior when `--yes` is absent.
- [x] 2.3 Add `houmao-mgr project mailbox clear-messages [--dry-run] [--yes]` as a selected-overlay wrapper over the shared helper.
- [x] 2.4 Ensure `mailbox --help` and `project mailbox --help` list `clear-messages` separately from `cleanup`.

## 3. Docs And Skill Guidance

- [x] 3.1 Update mailbox CLI/reference docs to explain `clear-messages`, account preservation, dry-run/confirmation behavior, and the distinction from `cleanup`.
- [x] 3.2 Add a `houmao-mailbox-mgr` action page for message clearing and link it from the skill index.
- [x] 3.3 Update mailbox-admin skill guardrails so delivered-message reset requests route to `clear-messages` instead of account unregister, registration cleanup, or ad hoc filesystem edits.

## 4. Verification

- [x] 4.1 Add mailbox-managed unit tests for dry-run, apply, idempotent rerun, registration preservation, local mailbox state reset, projection removal, private symlink mailbox preservation, and external `path_ref` attachment preservation.
- [x] 4.2 Add top-level CLI tests covering help output, `--dry-run`, `--yes`, and non-interactive apply without `--yes`.
- [x] 4.3 Add project mailbox CLI tests covering selected-overlay root resolution and account preservation.
- [x] 4.4 Run targeted mailbox and CLI tests, then run `openspec status --change add-mailbox-message-clear-command` and any available OpenSpec validation for the change.
