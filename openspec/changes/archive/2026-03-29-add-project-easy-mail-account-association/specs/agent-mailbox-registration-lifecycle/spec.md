## ADDED Requirements

### Requirement: Symlink-backed filesystem registrations validate and safely prepare explicit private mailbox directories

When a filesystem mailbox registration request uses `mailbox_kind = symlink`, the filesystem mailbox transport SHALL treat the requested `mailbox_path` as the concrete mailbox directory for that full mailbox address and SHALL resolve that path before registration mutates shared mailbox state.

The filesystem mailbox transport SHALL reject a symlink-backed registration request when the resolved concrete mailbox directory is inside the resolved shared mailbox root.

The filesystem mailbox transport SHALL reject a symlink-backed registration request when the shared-root mailbox entry for the requested address already exists as:

- a real directory, or
- a symlink to a different concrete mailbox directory.

The filesystem mailbox transport SHALL reuse the registration idempotently when the requested address already has a matching active or inactive symlink-backed registration for the same owner identity and the same resolved concrete mailbox directory.

The filesystem mailbox transport SHALL allow at most one active mailbox registration for a given resolved concrete symlink-backed mailbox directory across all addresses.

When a symlink-backed registration request targets a concrete mailbox directory that already exists, the transport SHALL prepare that directory non-destructively by:

- creating the directory if it does not yet exist,
- creating any missing standard placeholder directories required by the filesystem mailbox contract,
- preserving unrelated existing files,
- preserving existing mailbox-local SQLite state instead of silently resetting it during safe adoption.

#### Scenario: Safe symlink registration reuses a matching existing mailbox binding
- **WHEN** a participant registers mailbox address `AGENTSYS-bob@agents.localhost` in `safe` mode with `mailbox_kind = symlink`
- **AND WHEN** that address already has a matching symlink-backed active registration for the same owner identity and the same resolved mailbox directory
- **THEN** the filesystem mailbox transport reuses that registration idempotently
- **AND THEN** it does not recreate or retarget the existing symlink-backed mailbox entry

#### Scenario: Safe symlink registration rejects a concrete mailbox directory inside the shared root
- **WHEN** a participant registers mailbox address `AGENTSYS-bob@agents.localhost` in `safe` mode with `mailbox_kind = symlink`
- **AND WHEN** the requested concrete mailbox directory resolves inside the shared mailbox root
- **THEN** the filesystem mailbox transport fails explicitly before mutating registration state
- **AND THEN** the error explains that a private symlink target must live outside the shared mailbox root

#### Scenario: Safe symlink registration fails when the address slot is occupied by a different artifact
- **WHEN** a participant registers mailbox address `AGENTSYS-bob@agents.localhost` in `safe` mode with `mailbox_kind = symlink`
- **AND WHEN** `mailboxes/AGENTSYS-bob@agents.localhost` already exists as a real directory or as a symlink to a different concrete mailbox directory
- **THEN** the filesystem mailbox transport fails explicitly
- **AND THEN** it does not silently replace or retarget the conflicting mailbox artifact

#### Scenario: Safe symlink registration rejects reuse of one private mailbox directory by a different active address
- **WHEN** mailbox address `AGENTSYS-alice@agents.localhost` already has an active symlink-backed registration whose concrete mailbox directory is `/tmp/private-mail/shared-account`
- **AND WHEN** a participant attempts to register mailbox address `AGENTSYS-bob@agents.localhost` in `safe` mode with that same concrete mailbox directory
- **THEN** the filesystem mailbox transport fails explicitly
- **AND THEN** the error explains that one concrete private mailbox directory cannot be shared by multiple active mailbox addresses

#### Scenario: Safe symlink registration prepares an existing non-empty mailbox directory non-destructively
- **WHEN** a participant registers mailbox address `AGENTSYS-bob@agents.localhost` in `safe` mode with `mailbox_kind = symlink`
- **AND WHEN** the requested concrete mailbox directory already exists and already contains mailbox-local files
- **THEN** the filesystem mailbox transport creates any missing standard placeholder directories required by the filesystem mailbox contract
- **AND THEN** it preserves the existing mailbox-local SQLite state instead of silently resetting it during registration
