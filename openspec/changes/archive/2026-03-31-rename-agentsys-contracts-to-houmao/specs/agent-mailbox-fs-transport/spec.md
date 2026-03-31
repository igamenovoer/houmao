## MODIFIED Requirements

### Requirement: Filesystem mailbox transport uses a configurable mailbox content root with deterministic internal layout
The filesystem mailbox transport SHALL persist mailbox artifacts under a mailbox content root that is configurable through runtime mailbox binding inputs rather than through mailbox-specific session env publication.

When no explicit mailbox content root is configured, the filesystem mailbox transport SHALL default that content root to the Houmao mailbox root `~/.houmao/mailbox` rather than deriving it from the runtime root.

When no explicit mailbox content root is configured and `HOUMAO_GLOBAL_MAILBOX_DIR` is set to an absolute directory path, the effective Houmao mailbox root SHALL be derived from that env-var override before runtime persists or resolves filesystem mailbox state for the session.

The filesystem mailbox transport SHALL require a symlink-capable local filesystem for address-based mailbox registration and mailbox projection writes.

#### Scenario: Mailbox-root env-var override redirects the default mailbox root
- **WHEN** `HOUMAO_GLOBAL_MAILBOX_DIR` is set to `/tmp/houmao-mailbox`
- **AND WHEN** a filesystem mailbox transport is initialized without an explicit mailbox content root setting
- **THEN** the system derives the effective filesystem mailbox content root from `/tmp/houmao-mailbox`
- **AND THEN** the resulting mailbox subtree uses that env-var-selected location while preserving the same internal layout

