## 1. Core Export Behavior

- [x] 1.1 Add mailbox export request/result/action modeling for account selection, output directory, symlink mode, copied artifacts, materialized artifacts, preserved symlinks, skipped artifacts, and blocked artifacts.
- [x] 1.2 Implement export account selection from the shared mailbox index for `--all-accounts` and repeated selected addresses, including explicit validation for missing or conflicting scope.
- [x] 1.3 Implement the locked export snapshot flow that acquires selected address locks, acquires the shared index lock, re-reads selected state, and rejects mailbox roots that need repair.
- [x] 1.4 Implement archive writing through a temporary output directory, final publish to a non-existing output directory, and failure cleanup for partial temporary output.
- [x] 1.5 Implement default symlink materialization for projection symlinks and symlink-backed account directories, including a final no-symlink verification pass.
- [x] 1.6 Implement explicit `preserve` symlink mode for archive-internal relative projection links, including clear failure when the target filesystem cannot create symlinks.
- [x] 1.7 Implement managed-copy attachment copying and external `path_ref` manifest-only recording, including blocked records for managed-copy paths outside the mailbox managed attachment directory.
- [x] 1.8 Write `manifest.json` with source root, protocol version, timestamp, account selection, symlink mode, registration metadata, message mappings, projection mappings, attachment mappings, skipped artifacts, and blocked artifacts.

## 2. CLI Plumbing

- [x] 2.1 Add a shared command helper in `mailbox_support.py` that invokes the export helper and returns a structured export payload.
- [x] 2.2 Add `houmao-mgr mailbox export --output-dir <dir> (--all-accounts | --address <full-address>...) [--mailbox-root <path>] [--symlink-mode materialize|preserve]`.
- [x] 2.3 Add validation and operator-facing failures for missing account scope, conflicting `--all-accounts` plus `--address`, existing output directories, and unsupported preserve-mode symlink creation.
- [x] 2.4 Add `houmao-mgr project mailbox export --output-dir <dir> (--all-accounts | --address <full-address>...) [--symlink-mode materialize|preserve]` as a selected-overlay wrapper over the shared helper.
- [x] 2.5 Ensure `mailbox --help` and `project mailbox --help` list `export` as a mailbox-root administration command.

## 3. Docs And Skill Guidance

- [x] 3.1 Update mailbox CLI/reference docs to explain export commands, account selection, output directory behavior, default no-symlink materialization, optional preserve mode, manifest contents, and attachment handling.
- [x] 3.2 Add a `houmao-mailbox-mgr` action page for mailbox export and link it from the skill index.
- [x] 3.3 Update mailbox-admin skill guardrails so archive/export requests route to `mailbox export` or `project mailbox export` instead of raw recursive filesystem copying.

## 4. Verification

- [x] 4.1 Add mailbox-managed unit tests for all-account export, selected-address export, manifest contents, existing-output failure, default no-symlink materialization, symlink-backed account materialization, preserve-mode relative projection symlinks, managed-copy attachment copying, external `path_ref` manifest-only recording, and blocked missing canonical files.
- [x] 4.2 Add generic mailbox CLI tests covering help output, account-scope validation, output-dir validation, structured payload fields, default materialized export, and preserve-mode reporting.
- [x] 4.3 Add project mailbox CLI tests covering selected-overlay root resolution, selected-address export, all-account export, and no fallback to the generic shared mailbox root.
- [x] 4.4 Add docs or skill packaging tests where existing test coverage asserts mailbox-admin skill action links or CLI reference command lists.
- [x] 4.5 Run targeted mailbox and CLI tests, then run `openspec status --change add-mailbox-export-command` and available OpenSpec validation for the change.
