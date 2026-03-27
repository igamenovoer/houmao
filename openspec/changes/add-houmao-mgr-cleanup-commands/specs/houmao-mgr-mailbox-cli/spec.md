## MODIFIED Requirements

### Requirement: `houmao-mgr mailbox` exposes local filesystem mailbox administration commands
`houmao-mgr` SHALL expose a top-level `mailbox` command family for local filesystem mailbox administration that does not require `houmao-server`.

At minimum, that family SHALL include:

- `init`
- `status`
- `register`
- `unregister`
- `repair`
- `cleanup`

The family SHALL target the filesystem mailbox transport only in v1.

#### Scenario: Operator sees the local mailbox administration commands
- **WHEN** an operator runs `houmao-mgr mailbox --help`
- **THEN** the help output lists `init`, `status`, `register`, `unregister`, `repair`, and `cleanup`
- **AND THEN** the command family is presented as a local mailbox administration surface rather than a server-backed API surface

## ADDED Requirements

### Requirement: `houmao-mgr mailbox cleanup` removes inactive or stashed registrations without deleting canonical messages
`houmao-mgr mailbox cleanup` SHALL clean up no-longer-relevant filesystem mailbox registrations under one resolved mailbox root without requiring `houmao-server`.

The effective mailbox root SHALL resolve from:

1. explicit `--mailbox-root`,
2. `AGENTSYS_GLOBAL_MAILBOX_DIR`,
3. the default shared mailbox root.

The command SHALL operate only on registrations whose status is `inactive` or `stashed`.

The command SHALL preserve:

- active mailbox registrations,
- canonical mailbox messages under `messages/`,
- mailbox roots that need repair rather than destructive cleanup.

The command SHALL accept `--dry-run`. In dry-run mode, it SHALL report matching registration and artifact cleanup candidates without deleting them.

#### Scenario: Dry-run reports inactive or stashed cleanup candidates without deleting canonical mail
- **WHEN** an operator runs `houmao-mgr mailbox cleanup --mailbox-root /tmp/shared-mail --dry-run`
- **AND WHEN** the mailbox root contains inactive or stashed registrations
- **THEN** the command reports those registrations as cleanup candidates
- **AND THEN** it does not delete canonical messages under `messages/` during that dry-run

#### Scenario: Cleanup removes inactive or stashed registrations
- **WHEN** an operator runs `houmao-mgr mailbox cleanup --mailbox-root /tmp/shared-mail`
- **AND WHEN** the mailbox root contains inactive or stashed registrations
- **THEN** the command removes the matching inactive or stashed registration state
- **AND THEN** the result reports which registrations were removed

#### Scenario: Active registration is preserved during cleanup
- **WHEN** an operator runs `houmao-mgr mailbox cleanup --mailbox-root /tmp/shared-mail`
- **AND WHEN** the mailbox root still contains an active registration for one mailbox address
- **THEN** the command preserves that active registration
- **AND THEN** the cleanup result does not report the active mailbox as removed
