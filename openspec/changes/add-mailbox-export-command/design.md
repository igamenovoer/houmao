## Context

The filesystem mailbox root is not a simple portable directory tree. Canonical delivered messages live under `messages/<YYYY-MM-DD>/`, shared metadata lives in `index.sqlite`, each resolved mailbox directory has its own `mailbox.sqlite`, mailbox projections under `inbox/` and `sent/` are symlinks to canonical messages, and an account entry under `mailboxes/<address>` can itself be a symlink to a private mailbox directory outside the shared root.

Operators currently have maintained commands for mailbox root lifecycle, registration lifecycle, structural message inspection, repair, cleanup, and delivered-message clearing. They do not have a maintained archive/export path. Copying the root directly is brittle because it can preserve symlink artifacts that the target archive filesystem cannot represent, can omit symlink-backed private mailbox state, or can accidentally preserve absolute symlink targets that are not useful outside the original machine.

## Goals / Non-Goals

**Goals:**

- Provide a maintained `mailbox export` command for generic and project-scoped filesystem mailbox roots.
- Export either all registered accounts or a selected set of addresses.
- Write an archive directory that is portable by default and contains no symlinks unless symlink preservation is explicitly requested.
- Preserve enough metadata in `manifest.json` to audit the export source, account selection, original registration paths, copied messages, copied attachments, skipped external `path_ref` attachments, and symlink handling.
- Keep the export non-destructive and serverless.
- Use the mailbox lock model so the archive is a consistent snapshot of the selected source state.

**Non-Goals:**

- Do not add a Stalwart mailbox export lane in this change.
- Do not add a mailbox import or restore command.
- Do not define a general backup format for all project overlay state.
- Do not copy external `path_ref` attachment targets by default.
- Do not require symlink support from the export target filesystem for the default export path.
- Do not make export repair inconsistent mailbox roots. Roots that need repair should fail clearly or export blocked artifacts rather than silently rebuilding state.

## Decisions

### Decision: Add a mailbox-managed export helper instead of raw copytree

The implementation should add a mailbox-managed export helper with structured result models. The helper should:

- resolve and validate the filesystem mailbox root,
- load selected registrations from `index.sqlite`,
- acquire selected address locks in lexicographic order and then `locks/index.lock`,
- re-read the selected index state while locked,
- copy or materialize selected artifacts into a temporary output directory,
- write `manifest.json`,
- verify the final default export tree contains no symlinks,
- atomically rename the temporary directory to the requested output directory when possible.

This keeps export aligned with the mailbox data model and avoids treating symlinks and private mailbox targets as ordinary tree entries.

Alternative considered: document `cp -a <mailbox-root> <archive-dir>`. Rejected because it preserves symlinks, misses the semantic account/message selection requirement, and can produce archives that cannot be unpacked on target filesystems without symlink support.

### Decision: Require explicit account selection

The CLI should require either `--all-accounts` or one or more `--address <full-address>` values. `--all-accounts` exports all registration rows from the mailbox index, including active, inactive, and stashed registrations when present. Address selection exports every registration row for the selected address values so archived metadata does not hide inactive or stashed history for that account.

For all-account export, the helper should include every canonical message known to the shared `messages` table. For selected-address export, the helper should include messages visible through `mailbox_projections` for the selected registration ids. If canonical files referenced by selected projection rows are missing, the manifest should record them as blocked rather than silently dropping them.

Alternative considered: make `--all-accounts` the default when no selection is passed. Rejected because export can copy substantial data and should make scope explicit.

### Decision: Archive is manifest-first and materialized by default

The archive should use a stable directory shape:

```text
<output-dir>/
  manifest.json
  messages/
    <YYYY-MM-DD>/
      <message-id>.md
  accounts/
    <address>/
      <registration-id>/
        account.json
        mailbox.sqlite
        inbox/
        sent/
        archive/
        drafts/
  attachments/
    managed/
      <attachment-id>/...
```

The manifest should record source paths and archive-relative paths for copied artifacts. Account directory names can use the normalized mailbox address because mailbox addresses are already validated as safe path segments, and the registration id avoids collisions across active, inactive, and stashed rows.

Projection symlinks should be materialized as regular Markdown files in default mode. Symlink-backed account directories should be copied as real account directories in default mode, with the original symlink entry and resolved target recorded in `account.json` and the root manifest.

Alternative considered: export only canonical messages plus a manifest and omit account directories. Rejected because operators asked to export selected accounts, and mailbox-local `mailbox.sqlite` state plus projected folder membership is account-scoped.

### Decision: Make symlink preservation explicit and bounded

The CLI should expose:

```text
--symlink-mode materialize|preserve
```

The default is `materialize`. In `preserve` mode, the helper may preserve projection links as archive-internal relative symlinks to the exported canonical message files. It should preserve only links whose target is also represented inside the archive. External symlink relationships, including private mailbox entry targets outside the source root, should be materialized into real directories unless a later change adds a more explicit external-symlink mode.

If the target filesystem does not support symlink creation in `preserve` mode, the command should fail clearly instead of silently falling back to materialization. Silent fallback would make the requested archive semantics ambiguous.

Alternative considered: preserve all source symlinks in preserve mode. Rejected because absolute external symlinks make the archive machine-specific and can point outside the exported tree.

### Decision: Treat managed-copy and path-ref attachments differently

Managed-copy attachments whose paths resolve under the mailbox root's managed attachment directory should be copied into `attachments/managed/` and mapped in the manifest.

External `path_ref` attachments should remain manifest-only in this change. The manifest should record their original absolute path, attachment metadata, and whether the referenced file existed at export time. This avoids copying arbitrary user files outside the mailbox root without an explicit future option and keeps the initial export semantics conservative.

Alternative considered: copy every readable `path_ref` target by default to maximize archive completeness. Rejected because `path_ref` is intentionally an external reference and may point at large, private, or unrelated files.

### Decision: Fail on pre-existing output directory

The initial command should require that `--output-dir` does not already exist. It should create a sibling temporary directory during export and rename it to the final output path only after a successful run. This avoids mixing stale archive content with a fresh export and avoids adding another destructive confirmation path to the first version.

Alternative considered: add `--replace-output --yes` immediately. Rejected as unnecessary for the first supported workflow; operators can choose a new archive directory or remove an old archive explicitly.

### Decision: Emit structured export payloads, not cleanup payloads

The export command should return a structured payload with fields such as:

- `schema_version`,
- `mailbox_root`,
- `output_dir`,
- `symlink_mode`,
- `selected_addresses`,
- `all_accounts`,
- `account_count`,
- `message_count`,
- `attachment_count`,
- `manifest_path`,
- `copied_artifacts`,
- `materialized_artifacts`,
- `preserved_symlinks`,
- `blocked_artifacts`,
- `skipped_artifacts`.

The existing cleanup payload shape is useful for destructive commands but is semantically awkward for export. Export should have its own action vocabulary while preserving the same general style of explicit action reporting.

Alternative considered: reuse cleanup payloads with `proposed_action="copy"`. Rejected because export is not cleanup and needs archive-specific summary fields and manifest references.

## Risks / Trade-offs

- [Risk] Export could race with delivery or mailbox-state mutation. -> Mitigation: acquire the selected address locks and shared index lock, then re-read the selected index state while locked before copying.
- [Risk] Large mailbox roots could make export slow. -> Mitigation: keep the operation streaming and deterministic where practical, report counts, and avoid expensive repair/reindex work inside export.
- [Risk] Selected-address export could omit stale canonical files that are not indexed. -> Mitigation: selected export is intentionally index-driven; all-account export can include every indexed canonical message. Stale unindexed files should be reported only when they intersect selected projection data or when future repair/export modes add broader corpus scanning.
- [Risk] Preserve mode could create non-portable archives. -> Mitigation: default to materialization and restrict preserve mode to archive-internal relative symlinks.
- [Risk] External `path_ref` attachments may surprise operators when not copied. -> Mitigation: record them explicitly in `manifest.json` and docs as skipped external references rather than silently ignoring them.
- [Risk] Failed export could leave partial temp output. -> Mitigation: use a deterministic temporary directory name, clean it up on failure where safe, and return blocked/failure diagnostics if cleanup cannot remove it.

## Migration Plan

No data migration is required. Existing filesystem mailbox roots remain valid, and the new export command is opt-in and non-destructive.

Rollback is straightforward: remove the export helper, CLI commands, docs, skill action, and tests. Archives created by this command are ordinary filesystem directories and remain inspectable even if the command is later removed.

## Open Questions

- Should a later change add `--copy-path-ref-attachments` for explicit external attachment copying?
- Should a later change add `--before`, `--after`, or `--message-id` filters, or keep account selection as the only export filter?
- Should a later change add an import/restore command that consumes this archive format?
