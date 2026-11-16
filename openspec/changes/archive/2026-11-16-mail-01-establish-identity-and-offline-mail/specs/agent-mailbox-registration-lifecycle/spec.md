# Spec Delta

## MODIFIED Requirements

### Requirement: Filesystem mailbox delivery routes through active mailbox registrations keyed by full address
Filesystem offline delivery SHALL resolve a full address through an active registration in the selected registry's mail store. Each registration SHALL bind the address, persisted owner `agent_id`, registration identity, mailbox kind, concrete path, and lifecycle status. At most one active owner SHALL exist per address within that authority.

Mutable state and projections SHALL belong to the concrete registration. Historical registrations SHALL remain distinct from later owners. Canonical recipient history SHALL preserve delivered address snapshots without depending on a live registration row. Delivery SHALL validate both sender and recipient membership before committing.

#### Scenario: Delivery resolves recipient through active mailbox address
- **WHEN** a registered sender delivers offline mail to `bob@houmao.localhost`
- **THEN** the selected registry resolves that exact address's active registration
- **AND THEN** it writes projections and mutable state only for that registration

#### Scenario: Delivery fails when no active mailbox registration exists for an address
- **WHEN** a sender targets an address without an active registration in its selected registry
- **THEN** delivery fails explicitly
- **AND THEN** it does not guess a path, consult another registry, or try online mail

#### Scenario: Purge preserves canonical recipient history
- **WHEN** an authorized operation purges an old registration
- **THEN** its registration-scoped projections and state can be removed
- **AND THEN** retained canonical recipient history remains independent of that registration row and is not exposed to a later owner

### Requirement: Filesystem mailbox leave and deregistration have defined cleanup semantics
Offline leave SHALL be an explicit authorized operation. It SHALL support non-destructive `deactivate` by default and explicit `purge` of registration-scoped state. Neither mode SHALL implicitly delete retained canonical messages or external symlink targets. Release SHALL retire the old registration's routing entry before another owner can claim the address, and reassignment SHALL isolate retained history from the new owner.

#### Scenario: Deactivate stops future delivery and preserves historical state
- **WHEN** an authorized owner deactivates its offline registration
- **THEN** further delivery fails until a valid active registration exists
- **AND THEN** retained historical state remains associated with the old registration

#### Scenario: Purge removes registration-scoped state without deleting canonical messages
- **WHEN** an authorized caller purges a released registration
- **THEN** its routing entry, projections, and mailbox-local state are removed as requested
- **AND THEN** retained canonical content is not deleted merely because the registration is removed

#### Scenario: Symlink deregistration does not delete the external target directory by default
- **WHEN** a symlink-backed registration is released
- **THEN** the registry retires the shared routing entry under its ownership rules
- **AND THEN** it does not recursively delete or retarget the external private directory

#### Scenario: New owner does not inherit the old inbox
- **WHEN** another agent claims a previously released address
- **THEN** it receives a fresh registration and mailbox view
- **AND THEN** old message references and retained old projections are inaccessible through the new registration

### Requirement: Symlink-backed filesystem registrations validate and safely prepare explicit private mailbox directories

When a filesystem mailbox registration request uses `mailbox_kind = symlink`, the filesystem mailbox transport SHALL treat the requested `mailbox_path` as the concrete mailbox directory for that full mailbox address and SHALL resolve that path before registration mutates shared mailbox state.

The filesystem mailbox transport SHALL reject a symlink-backed registration request when the resolved concrete mailbox directory is inside the resolved shared mailbox root.

The filesystem mailbox transport SHALL reject a symlink-backed registration request when the shared-root mailbox entry for the requested address already exists as:

- a real directory, or
- a symlink to a different concrete mailbox directory.

The filesystem mailbox transport SHALL reuse the registration idempotently when the requested address already has a matching active or recoverable preparing symlink-backed registration for the same owner identity and the same resolved concrete mailbox directory.

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

#### Scenario: Released symlink registration is not reactivated
- **WHEN** an authorized leave has released a symlink-backed registration and a later join is accepted
- **THEN** the later join receives a fresh registration identity instead of reactivating the released registration
- **AND THEN** retained private history stays isolated under its original registration and the external target is preserved

### Requirement: Filesystem mailbox lifecycle operations are published as managed mailbox helpers with structured JSON contracts
The shared filesystem mailbox root SHALL publish managed lifecycle helpers under `rules/scripts/` for registration and deregistration flows.

In the current-format surface, the managed lifecycle helper set SHALL include:

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
- **THEN** the helper accepts supported address, owner, and mailbox-path inputs in one JSON payload, with any explicit registration mode limited to `safe`
- **AND THEN** the helper emits one JSON result object that reports whether the registration was created or reused and identifies the resulting active registration

#### Scenario: Deregister helper uses a structured JSON payload and result
- **WHEN** an operator or agent invokes `deregister_mailbox.py`
- **THEN** the helper accepts a JSON payload that includes at least `mode` and `address`
- **AND THEN** the helper emits one JSON result object that reports the target registration and the resulting deregistration outcome such as `inactive` or `purged`

#### Scenario: Runtime bootstrap applies safe registration semantics
- **WHEN** the runtime starts or refreshes a mailbox-enabled session and must ensure that session's mailbox registration exists
- **THEN** the runtime applies the same semantic checks as `safe` join for the active session mailbox
- **AND THEN** bootstrap fails explicitly instead of silently overriding a conflicting active mailbox registration

## REMOVED Requirements

### Requirement: Filesystem mailbox join uses explicit conflict-resolution modes
**Reason**: Force/stash takeover contradicts exclusive offline address ownership and is intentionally removed.
**Migration**: Use conflict-rejecting join; release an address explicitly under its existing owner/admin authority before a fresh registration can claim it.

### Requirement: Refactored filesystem mailbox roots are hard-reset only within the intended v1 contract
**Reason**: The current ownership-aware filesystem format is version 4, so the earlier v1-only storage promise no longer applies.
**Migration**: Back up unsupported earlier roots and explicitly rebootstrap format 4 rather than migrating ownership implicitly.

### Requirement: Filesystem mailbox operations serialize on address-scoped locks
**Reason**: The old locking requirement includes a successful stash takeover that is no longer supported.
**Migration**: Use the replacement ownership-and-delivery locking contract; release an address explicitly before reassignment.

## ADDED Requirements

### Requirement: Offline join rejects occupied address takeover
Normal offline join SHALL use safe, conflict-rejecting registration semantics. A matching owner, address, and path SHALL be reused idempotently. A different owner or conflicting path SHALL cause failure without replacement. The former `force` and `stash` join modes SHALL be rejected. Address reassignment SHALL require prior authorized release and a fresh registration that cannot inherit another owner's private mailbox state.

#### Scenario: Safe join reuses an existing matching registration
- **WHEN** the same agent rejoins with a matching address and mailbox path
- **THEN** its existing registration is reused
- **AND THEN** messages and paths are neither deleted nor renamed

#### Scenario: Safe join fails on real identity or path conflict
- **WHEN** a requested address belongs to another agent or the requested path conflicts with the current registration
- **THEN** join fails explicitly without modifying existing ownership or artifacts

#### Scenario: Force join cannot take an occupied address
- **WHEN** a caller selects the removed `force` join mode
- **THEN** validation rejects it before registration or mailbox changes

#### Scenario: Stash join cannot take an occupied address
- **WHEN** a caller selects the removed `stash` join mode
- **THEN** validation rejects it without renaming the current owner's mailbox

### Requirement: Filesystem mailbox roots require the current ownership-aware format
Filesystem bootstrap and managed lifecycle operations SHALL reject unsupported earlier roots, including the old principal-keyed schema. They SHALL provide explicit backup and rebootstrap guidance instead of converting formats or inferring address ownership.

#### Scenario: Bootstrap rejects a stale principal-keyed or earlier-format mailbox root
- **WHEN** bootstrap or a managed lifecycle operation detects an earlier unsupported root
- **THEN** it fails with guidance to back up and explicitly rebootstrap the current format
- **AND THEN** it does not reset or convert the store automatically

### Requirement: Filesystem mailbox operations serialize ownership and delivery on address-scoped locks
Filesystem delivery, state mutation, registration, deregistration, and repair SHALL serialize on address locks under `locks/addresses/` rather than owner-principal locks. Mutations of registrations, registration-scoped state, or projections SHALL acquire every affected address lock in ascending full-address order before acquiring `locks/index.lock`.

#### Scenario: Delivery and explicit release serialize on the same address lock
- **WHEN** one process is delivering mail to `AGENTSYS-bob@agents.localhost`
- **AND WHEN** another process explicitly releases the registration for `AGENTSYS-bob@agents.localhost`
- **THEN** both operations serialize on the same address-scoped lock before either mutates mailbox projections or registration state
- **AND THEN** the system does not partially deliver into a released or reassigned registration

#### Scenario: Multi-address delivery acquires locks deterministically
- **WHEN** one mailbox operation affects multiple mailbox addresses
- **THEN** the operation acquires the corresponding address locks in ascending lexicographic full-address order before acquiring `locks/index.lock`
- **AND THEN** the operation fails explicitly rather than partially committing if it cannot obtain that lock set within the configured timeout
