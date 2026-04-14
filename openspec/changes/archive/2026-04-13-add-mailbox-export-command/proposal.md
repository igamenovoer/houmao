## Why

Operators need a maintained way to archive a filesystem mailbox root for demos, debugging, handoff, or recovery review without depending on the source filesystem layout. The current mailbox tree contains projection symlinks and optional symlink-backed private mailbox directories, so a raw directory copy is not portable across archive targets or filesystems that do not support symlinks.

## What Changes

- Add a serverless mailbox export workflow that writes a self-contained archive directory for one resolved filesystem mailbox root.
- Add `houmao-mgr mailbox export --output-dir <dir>` with account selection for repeated `--address <full-address>` values or `--all-accounts`.
- Add `houmao-mgr project mailbox export --output-dir <dir>` as a selected-overlay wrapper over the same export behavior.
- Default exported artifacts to symlink materialization so the target tree contains regular files and directories rather than symlink artifacts.
- Add an optional symlink preservation mode for operators who explicitly want symlinks and whose target filesystem supports them.
- Include an export manifest that records source root, selected accounts, registration metadata, message mappings, attachment mappings, symlink policy, copied/skipped artifacts, and blocked artifacts.
- Treat managed-copy attachments under the mailbox root as exportable content, while keeping external `path_ref` attachment targets manifest-only unless an explicit future option chooses to copy them.
- Update mailbox-admin skill guidance and mailbox reference docs so agents and operators use the maintained export command instead of ad hoc filesystem copying.

## Capabilities

### New Capabilities

- `filesystem-mailbox-export-archive`: Defines the portable filesystem mailbox export archive contract, including account selection, archive structure, manifest metadata, attachment handling, and symlink materialization policy.

### Modified Capabilities

- `houmao-mgr-mailbox-cli`: Add the generic filesystem mailbox `export` command and define its account-selection and output-dir behavior.
- `houmao-mgr-project-mailbox-cli`: Add the project-scoped `export` wrapper over the selected overlay mailbox root.
- `houmao-mailbox-mgr-skill`: Teach the packaged mailbox-admin skill to route mailbox archive/export requests to the new maintained command.
- `mailbox-reference-docs`: Document the supported mailbox export workflow, archive structure, symlink policy, and boundary from raw mailbox-root copying.

## Impact

- Affected CLI modules: `src/houmao/srv_ctrl/commands/mailbox.py`, `src/houmao/srv_ctrl/commands/project_mailbox.py`, and shared helpers in `src/houmao/srv_ctrl/commands/mailbox_support.py`.
- Affected mailbox logic: `src/houmao/mailbox/managed.py` or a nearby filesystem mailbox export helper that can lock the source root and materialize the archive safely.
- Affected docs and skills: mailbox CLI/reference docs and `src/houmao/agents/assets/system_skills/houmao-mailbox-mgr/`.
- Tests should cover archive structure, selected-account and all-account exports, default no-symlink materialization, optional symlink preservation, manifest content, managed-copy attachment copying, external `path_ref` handling, generic CLI behavior, and project wrapper behavior.
