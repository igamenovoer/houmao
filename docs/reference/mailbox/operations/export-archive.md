# Mailbox Export Archive

Use the maintained export commands when you need to archive filesystem mailbox state for demos, debugging, handoff, or recovery review:

```bash
houmao-mgr mailbox export --mailbox-root /abs/path/shared-mail --output-dir /abs/path/archive --all-accounts
houmao-mgr mailbox export --mailbox-root /abs/path/shared-mail --output-dir /abs/path/alice-archive --address alice@houmao.localhost
houmao-mgr project mailbox export --output-dir /abs/path/project-mailbox-archive --all-accounts
```

The command requires explicit scope. Use `--all-accounts` to export every registration row and every canonical message known to the shared mailbox index, or repeat `--address <full-address>` to export every registration row for selected addresses and the messages visible through their projection rows. Do not use raw recursive mailbox-root copying for this workflow: the filesystem mailbox root contains projection symlinks and can contain symlink-backed private mailbox directories, so a raw copy can produce an archive that is not portable or that misses account-local state outside the shared root.

The output directory must not already exist. Export writes into a sibling temporary directory first, writes `manifest.json`, verifies the default materialized archive, and then publishes the final output directory.

Default export mode is `--symlink-mode materialize`. This materializes projection symlinks as regular Markdown files and materializes symlink-backed account directories as real archive directories. The final default archive is verified to contain no symlink artifacts, which keeps it usable on filesystems and archive targets that do not support symlinks.

Use `--symlink-mode preserve` only when the user explicitly wants supported symlinks and the target filesystem can create them. Preserve mode is bounded: it preserves archive-internal relative projection links to canonical message files that are also present in the archive. It does not preserve external private-mailbox symlink targets as external links.

The archive shape is:

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

`manifest.json` records the source mailbox root, source protocol version, export timestamp, account selection, symlink mode, selected registration metadata, original mailbox paths, archive-relative account paths, canonical message mappings, projection mappings, mailbox-local SQLite mappings, attachment mappings, skipped artifacts, and blocked artifacts.

Managed-copy attachments are copied only when their recorded path resolves under the mailbox root's managed attachment directory. External `path_ref` attachment targets are not copied by default; they are recorded in the manifest with the original path and whether the target existed at export time. A managed-copy attachment path outside the managed attachment directory is blocked and recorded rather than copied.

## Source References

- [`src/houmao/mailbox/managed.py`](../../../../src/houmao/mailbox/managed.py)
- [`src/houmao/srv_ctrl/commands/mailbox.py`](../../../../src/houmao/srv_ctrl/commands/mailbox.py)
- [`src/houmao/srv_ctrl/commands/project_mailbox.py`](../../../../src/houmao/srv_ctrl/commands/project_mailbox.py)
