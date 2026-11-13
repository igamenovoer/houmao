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

## REMOVED Requirements

### Requirement: Filesystem mailbox join uses explicit conflict-resolution modes
**Reason**: Force/stash takeover contradicts exclusive offline address ownership and is intentionally removed.
**Migration**: Use conflict-rejecting join; release an address explicitly under its existing owner/admin authority before a fresh registration can claim it.

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
