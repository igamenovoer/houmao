## ADDED Requirements

### Requirement: Refactored filesystem mailbox roots are hard-reset only within the intended v1 contract
The filesystem mailbox registration refactor SHALL remain part of the intended `v1` mailbox contract.

Filesystem mailbox roots created by the earlier principal-keyed implementation SHALL be treated as unsupported stale roots rather than as migration inputs.

When bootstrap or a managed lifecycle operation can detect that stale principal-keyed layout, it SHALL fail explicitly and direct the operator to delete and re-bootstrap the mailbox root.

#### Scenario: Bootstrap rejects a stale principal-keyed mailbox root
- **WHEN** the runtime bootstraps or refreshes a filesystem mailbox root that still uses the earlier principal-keyed registration schema
- **THEN** the mailbox operation fails explicitly
- **AND THEN** the error directs the operator to delete and re-bootstrap the mailbox root rather than attempting an in-place migration

### Requirement: Filesystem mailbox delivery routes through active mailbox registrations keyed by full address
The filesystem mailbox transport SHALL route delivery by full mailbox address rather than by short agent name or owner principal id alone.

Each concrete mailbox registration SHALL bind at minimum:

- one full mailbox address,
- one owner `principal_id`,
- one mailbox kind,
- one concrete mailbox path,
- one lifecycle status.

The filesystem mailbox transport SHALL allow historical mailbox registrations for the same owner or address, but it SHALL allow at most one `active` mailbox registration for a given full mailbox address at a time.

Registration-scoped mutable mailbox state and mailbox projections SHALL attach to the concrete mailbox registration rather than only to owner-principal identity.

Canonical recipient history SHALL remain address-snapshot-oriented and SHALL NOT depend on a live mailbox-registration row continuing to exist.

#### Scenario: Delivery resolves recipient through active mailbox address
- **WHEN** a sender delivers a mailbox message to `AGENTSYS-bob@agents.localhost`
- **THEN** the filesystem mailbox transport resolves the recipient through the active mailbox registration for that exact address
- **AND THEN** delivery writes mailbox projections and mutable mailbox state for that resolved active registration

#### Scenario: Delivery fails when no active mailbox registration exists for an address
- **WHEN** a sender attempts delivery to a full mailbox address that has no active mailbox registration
- **THEN** the filesystem mailbox transport fails that delivery explicitly
- **AND THEN** the system does not guess a mailbox path from a short name or owner principal id

#### Scenario: Purge preserves canonical recipient history
- **WHEN** an operator later purges a mailbox registration that previously received delivered mail
- **THEN** the registration-scoped mailbox state and mailbox projections may be removed
- **AND THEN** canonical message and recipient history remain queryable without depending on that live registration row

### Requirement: Filesystem mailbox join uses explicit conflict-resolution modes
The filesystem mailbox transport SHALL expose explicit join or registration conflict-resolution modes for mailbox registration under a shared mailbox root.

The supported join modes SHALL be:

- `safe`
- `force`
- `stash`

Join mode `safe` SHALL be the default.

#### Scenario: Safe join reuses an existing matching registration
- **WHEN** a participant joins a mailbox group in `safe` mode
- **AND WHEN** the existing active mailbox registration for that address already matches the joining owner identity and expected mailbox path
- **THEN** the filesystem mailbox transport reuses that registration idempotently
- **AND THEN** the join does not delete or rename existing mailbox artifacts

#### Scenario: Safe join fails on real identity or path conflict
- **WHEN** a participant joins a mailbox group in `safe` mode
- **AND WHEN** the target address is already bound to a different active mailbox registration
- **THEN** the join fails explicitly
- **AND THEN** the system does not silently adopt, delete, or rename the conflicting mailbox artifact

#### Scenario: Force join replaces the conflicting active registration
- **WHEN** a participant joins a mailbox group in `force` mode for an address that already has an active mailbox registration
- **THEN** the filesystem mailbox transport replaces that active registration with a fresh active mailbox registration for the joining participant
- **AND THEN** the replacement is recorded explicitly in mailbox registration state rather than treated as an implicit bootstrap side effect

#### Scenario: Stash join preserves the previous mailbox artifact
- **WHEN** a participant joins a mailbox group in `stash` mode for an address that already has an active mailbox registration
- **THEN** the filesystem mailbox transport renames the previous mailbox artifact by suffixing a UUID4 hex token
- **AND THEN** the previous registration is marked as `stashed`
- **AND THEN** the system creates a fresh active mailbox registration for the original address without rewriting canonical message files

### Requirement: Filesystem mailbox leave and deregistration have defined cleanup semantics
The filesystem mailbox transport SHALL provide an explicit deregistration surface for removing a participant from future delivery in a protocol-defined way.

The supported leave modes SHALL be:

- `deactivate`
- `purge`

Leave mode `deactivate` SHALL be the safe default.

#### Scenario: Deactivate stops future delivery and preserves historical state
- **WHEN** an operator or agent deregisters a mailbox in `deactivate` mode
- **THEN** the mailbox registration transitions from `active` to `inactive`
- **AND THEN** future deliveries to that address fail until a new active registration exists
- **AND THEN** canonical messages and historical registration-scoped mailbox artifacts remain available for inspection

#### Scenario: Purge removes registration-scoped state without deleting canonical messages
- **WHEN** an operator or agent deregisters a mailbox in `purge` mode
- **THEN** the filesystem mailbox transport removes the shared-root registration entry and registration-scoped mutable state for that mailbox
- **AND THEN** canonical messages under `messages/` remain unchanged
- **AND THEN** the cleanup result reports that future delivery requires a new active mailbox registration

#### Scenario: Symlink deregistration does not delete the external target directory by default
- **WHEN** an operator or agent deregisters a symlink-backed mailbox registration
- **THEN** the filesystem mailbox transport removes or deactivates the shared-root registration for that mailbox according to the selected leave mode
- **AND THEN** the system does not recursively delete the external private mailbox target directory by default

### Requirement: Filesystem mailbox operations serialize on address-scoped locks
The filesystem mailbox transport SHALL serialize delivery, mailbox-state mutation, registration, deregistration, and repair flows on mailbox-address locks rather than on owner-principal locks.

The shared filesystem mailbox root SHALL expose those locks under `locks/addresses/`.

Any operation that mutates mailbox registrations, registration-scoped mutable state, or mailbox projections SHALL acquire all affected address locks in ascending lexicographic full-address order before acquiring `locks/index.lock`.

#### Scenario: Delivery and stash join serialize on the same address lock
- **WHEN** one process is delivering mail to `AGENTSYS-bob@agents.localhost`
- **AND WHEN** another process attempts a `stash` join for `AGENTSYS-bob@agents.localhost`
- **THEN** both operations serialize on the same address-scoped lock before either mutates mailbox projections or registration state
- **AND THEN** the system does not partially deliver into a mailbox path that is being replaced

#### Scenario: Multi-address delivery acquires locks deterministically
- **WHEN** one mailbox operation affects multiple mailbox addresses
- **THEN** the operation acquires the corresponding address locks in ascending lexicographic full-address order before acquiring `locks/index.lock`
- **AND THEN** the operation fails explicitly rather than partially committing if it cannot obtain that lock set within the configured timeout

### Requirement: Filesystem mailbox directories and lock names use literal full addresses with safe path-segment validation
The filesystem mailbox transport SHALL use the literal full mailbox address for `mailboxes/<address>/` and `locks/addresses/<address>.lock`.

The system SHALL centralize one shared helper that validates whether a mailbox address is safe to use as a literal filesystem path segment before it is used for directory names or lock names.

The filesystem mailbox transport SHALL reject mailbox addresses that fail that safe path-segment validation rather than encoding them into an alternate name in `v1`.

#### Scenario: Safe full mailbox address becomes literal mailbox directory name
- **WHEN** a participant registers a mailbox address that passes safe path-segment validation
- **THEN** the active mailbox directory is created or validated under `mailboxes/<address>/`
- **AND THEN** the corresponding lock file path is derived from that same literal address under `locks/addresses/`

#### Scenario: Unsafe address is rejected before filesystem registration
- **WHEN** a participant attempts to register or use a mailbox address that is not safe as one literal filesystem path segment
- **THEN** the operation fails explicitly before creating mailbox directories or lock files
- **AND THEN** the system does not silently encode that address into an alternate filesystem name

### Requirement: Filesystem mailbox lifecycle operations are published as managed mailbox helpers with structured JSON contracts
The shared filesystem mailbox root SHALL publish managed lifecycle helpers under `rules/scripts/` for registration and deregistration flows.

In this refactored v1 surface, the managed lifecycle helper set SHALL include:

- `register_mailbox.py`
- `deregister_mailbox.py`

If those helpers are Python-based, `rules/scripts/requirements.txt` SHALL declare the dependencies needed to run them.

Each managed lifecycle helper SHALL follow the same structural contract as the existing mailbox-local managed helpers:

- accept `--mailbox-root`
- accept `--payload-file`
- load one JSON payload from that file
- emit exactly one JSON object to stdout

The runtime-owned bootstrap path for a new or resumed mailbox-enabled session SHALL use the same registration semantics as `safe` join when it needs to register the active session mailbox.

#### Scenario: Managed lifecycle helpers are materialized with the mailbox rules asset set
- **WHEN** the runtime initializes or validates a filesystem mailbox root for this protocol version
- **THEN** the shared mailbox `rules/scripts/` directory contains `register_mailbox.py` and `deregister_mailbox.py`
- **AND THEN** the shared mailbox also contains `rules/scripts/requirements.txt` describing Python dependencies needed by those helpers

#### Scenario: Register helper uses a structured JSON payload and result
- **WHEN** an operator or agent invokes `register_mailbox.py`
- **THEN** the helper accepts a JSON payload that includes at least `mode`, `address`, `owner_principal_id`, `mailbox_kind`, and `mailbox_path`
- **AND THEN** the helper emits one JSON result object that reports whether the registration was reused, replaced, or stashed and identifies the resulting active registration

#### Scenario: Deregister helper uses a structured JSON payload and result
- **WHEN** an operator or agent invokes `deregister_mailbox.py`
- **THEN** the helper accepts a JSON payload that includes at least `mode` and `address`
- **AND THEN** the helper emits one JSON result object that reports the target registration and the resulting deregistration outcome such as `inactive` or `purged`

#### Scenario: Runtime bootstrap applies safe registration semantics
- **WHEN** the runtime starts or refreshes a mailbox-enabled session and must ensure that session's mailbox registration exists
- **THEN** the runtime applies the same semantic checks as `safe` join for the active session mailbox
- **AND THEN** bootstrap fails explicitly instead of silently overriding a conflicting active mailbox registration
