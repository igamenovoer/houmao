## ADDED Requirements

### Requirement: Filesystem mailbox startup can target either the shared-root mailbox path or an explicit private mailbox directory

For filesystem mailbox-enabled session startup, the runtime SHALL support a transport-specific registration target that distinguishes between:

- `in_root`
- `symlink`

When filesystem startup uses `in_root`, the runtime SHALL bootstrap or confirm the mailbox registration at the shared-root mailbox entry for the session's mailbox address.

When filesystem startup uses `symlink`, the runtime SHALL bootstrap or confirm the mailbox registration at the shared-root mailbox entry for the session's mailbox address while using the resolved explicit mailbox directory as the concrete mailbox path.

The runtime SHALL validate that explicit filesystem mailbox target before session startup commits, SHALL preserve the selected filesystem mailbox kind and concrete mailbox path in the resolved filesystem mailbox configuration, and SHALL persist that resolved binding so resume restores the same mailbox association shape.

The runtime SHALL reject a filesystem `symlink` mailbox target whose resolved concrete mailbox path is inside the resolved filesystem mailbox root.

If filesystem mailbox bootstrap fails for the selected target, session startup SHALL fail explicitly and SHALL NOT report a successful started session.

#### Scenario: Start session persists a symlink-backed filesystem mailbox binding
- **WHEN** a developer starts a filesystem mailbox-enabled session with an explicit private mailbox directory outside the shared mailbox root
- **THEN** the runtime bootstraps that mailbox association as a `symlink` filesystem mailbox binding
- **AND THEN** the resolved session manifest preserves the filesystem mailbox kind and concrete mailbox directory needed to restore that same binding on resume

#### Scenario: Resume restores the persisted symlink-backed filesystem mailbox binding
- **WHEN** a developer resumes a previously started filesystem mailbox-enabled session whose persisted mailbox binding used an explicit private mailbox directory
- **THEN** the runtime restores that same filesystem mailbox kind and concrete mailbox path from the session manifest
- **AND THEN** subsequent mailbox-aware runtime work uses the same shared-root mailbox entry and private mailbox directory association

#### Scenario: Start session rejects a private mailbox directory inside the mailbox root
- **WHEN** a developer starts a filesystem mailbox-enabled session with a requested private mailbox directory that resolves inside the selected shared mailbox root
- **THEN** session startup fails explicitly before reporting success
- **AND THEN** the error explains that the private mailbox directory must live outside the shared mailbox root
