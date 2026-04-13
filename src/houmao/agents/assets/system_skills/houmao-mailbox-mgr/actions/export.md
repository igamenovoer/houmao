# Export Mailbox Archive

Use this action only when the user wants to archive or export filesystem mailbox state from one arbitrary mailbox root or from the active project mailbox root.

## Workflow

1. Determine whether the task targets one arbitrary filesystem mailbox root or the active project mailbox root.
2. Require a new output directory path.
3. Require explicit account scope:
   - use `--all-accounts` when the user wants the whole mailbox root
   - use repeated `--address <full-address>` values when the user selected specific accounts
4. Use default symlink materialization unless the user explicitly asks to preserve supported symlinks.
5. Run the matching mailbox export command.
6. Report the output directory, manifest path, selected scope, symlink mode, and any blocked or skipped artifacts.

## Commands

Use the `houmao-mgr` launcher already chosen by the top-level skill.

```bash
<chosen houmao-mgr launcher> mailbox export [--mailbox-root <path>] --output-dir <dir> (--all-accounts | --address <full-address>...) [--symlink-mode materialize|preserve]
<chosen houmao-mgr launcher> project mailbox export --output-dir <dir> (--all-accounts | --address <full-address>...) [--symlink-mode materialize|preserve]
```

Default export uses `--symlink-mode materialize`, which writes regular files and directories and verifies that the archive contains no symlink artifacts. This is the right default for archives that may move across filesystem formats.

Only add `--symlink-mode preserve` when the user explicitly wants symlink preservation and the target filesystem supports symlink creation. Preserve mode is bounded to archive-internal relative projection symlinks; external private mailbox symlink targets are still materialized.

Managed-copy attachments under the mailbox root's managed attachment directory are copied. External `path_ref` attachments are manifest-only by default and should not be copied with ad hoc filesystem commands.

## Guardrails

- Do not guess the output directory.
- Do not guess export scope; choose `--all-accounts` only when the user asked for the whole root, otherwise preserve selected addresses.
- Do not recommend raw recursive mailbox-root copying for archive/export requests covered by this command.
- Do not add `--symlink-mode preserve` unless the user explicitly asked for symlink preservation.
