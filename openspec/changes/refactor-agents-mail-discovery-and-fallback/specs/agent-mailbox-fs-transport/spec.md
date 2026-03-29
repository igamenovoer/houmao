## MODIFIED Requirements

### Requirement: Filesystem mailbox initialization is a runtime-owned bootstrap path
The system SHALL initialize a new filesystem mailbox root through package-internal runtime bootstrap code that does not depend on pre-existing helper scripts under `rules/scripts/`.

That bootstrap path SHALL create or validate at minimum:

- `protocol-version.txt`
- the SQLite schema
- the `rules/` tree and mailbox-local policy documents
- the locks area
- the staging area
- any in-root address-based mailbox directories and mailbox-registration entries being initialized

The runtime MAY also publish compatibility or diagnostic helper assets under `rules/scripts/`, but ordinary mailbox operation SHALL NOT depend on those assets being the public execution contract.

On an existing mailbox root, bootstrap SHALL validate `protocol-version.txt` before continuing and SHALL fail explicitly when the on-disk protocol version is unsupported.

#### Scenario: Bootstrap materializes a new mailbox root without pre-existing helper scripts
- **WHEN** the runtime initializes a new filesystem mailbox root that does not yet contain shared mailbox helper scripts
- **THEN** the runtime performs bootstrap directly through package-internal code rather than invoking pre-existing `rules/scripts/` helpers
- **AND THEN** the resulting mailbox root contains the initialized SQLite schema, `protocol-version.txt`, and mailbox-local `rules/` policy content needed for later mailbox operations

#### Scenario: Bootstrap creates initial in-root mailbox registration
- **WHEN** the runtime initializes mailbox support for a participant that uses an in-root mailbox directory for one full mailbox address
- **THEN** the runtime bootstrap path creates that mailbox directory structure directly
- **AND THEN** the bootstrap path records the corresponding in-root mailbox registration in the mailbox index without requiring pre-existing shared helper scripts

#### Scenario: Unsupported protocol version fails bootstrap
- **WHEN** the runtime encounters an existing filesystem mailbox root whose `protocol-version.txt` value is unsupported by the current implementation
- **THEN** bootstrap fails explicitly before mutating that mailbox root
- **AND THEN** the runtime does not proceed with partial initialization against the unsupported on-disk protocol

### Requirement: Filesystem mailbox root publishes shared mailbox rules
The filesystem mailbox transport SHALL publish a `rules/` directory under the mailbox root as the mailbox-local source of truth for shared mailbox policy guidance.

That `rules/` directory SHALL contain at minimum:

- a human-readable `README`
- mailbox-local markdown guidance

That guidance MAY cover:

- message formatting,
- reply or subject conventions,
- mailbox-local etiquette,
- other workflow hints specific to that mailbox.

The filesystem mailbox public contract SHALL NOT require `rules/` to carry the canonical execution protocol for ordinary send, reply, check, or mark-read operations.

The transport MAY publish compatibility or diagnostic assets under `rules/scripts/`, but it SHALL NOT require a stable public `rules/scripts/` filename set for ordinary agent or operator mailbox work.

#### Scenario: Filesystem mailbox root exposes mailbox-local policy guidance
- **WHEN** a participant inspects the shared filesystem mailbox root before mailbox interaction
- **THEN** the participant can find a `rules/` directory under that mailbox root
- **AND THEN** that `rules/` directory contains mailbox-local policy guidance that can refine formatting or workflow expectations without becoming the canonical execution protocol

#### Scenario: Ordinary mailbox workflow does not require shared scripts
- **WHEN** an agent or operator performs an ordinary filesystem mailbox action through the supported Houmao-owned workflow
- **THEN** the action can complete without requiring the caller to discover or invoke a mailbox-owned script under `rules/scripts/`
- **AND THEN** the participant does not need to reconstruct the mailbox protocol from script names or dependency manifests

### Requirement: Filesystem transport is daemon-free and synchronizes writes with lock files
The filesystem mailbox transport SHALL NOT require a background process for delivery or mailbox-state updates.

The transport SHALL coordinate concurrent filesystem writers using deterministic `.lock` files and SHALL combine multi-file delivery changes with transactional SQLite index updates.

Standardized filesystem write flows executed by Houmao-owned code SHALL acquire all affected address locks in ascending lexicographic full-address order before acquiring `locks/index.lock`.

Ordinary agent-facing filesystem mailbox workflows SHALL reach those writes through gateway HTTP or `houmao-mgr agents mail ...` rather than through mailbox-owned scripts.

#### Scenario: Sender delivers mail without a helper daemon
- **WHEN** a sender process writes a mailbox message through the filesystem transport
- **THEN** the sender performs delivery directly through filesystem and SQLite operations
- **AND THEN** the delivery does not depend on a persistent helper daemon being active

#### Scenario: Ordinary filesystem mailbox workflow uses Houmao-owned surfaces
- **WHEN** an agent sender interacts with a shared filesystem mailbox through the supported ordinary mailbox workflow
- **THEN** that workflow uses the shared gateway facade when present or `houmao-mgr agents mail ...` when it is not
- **AND THEN** the caller does not need to invoke a mailbox-owned script under `rules/scripts/` for the ordinary operation

#### Scenario: Concurrent writers serialize conflicting mailbox updates
- **WHEN** two sender processes attempt to update the same mailbox address concurrently
- **THEN** the system serializes conflicting writes using deterministic lock files
- **AND THEN** recipients do not observe partially applied mailbox projections for a committed delivery

#### Scenario: Lock acquisition order avoids deadlock
- **WHEN** a standardized filesystem mailbox write affects multiple mailbox addresses
- **THEN** the Houmao-owned write flow acquires the corresponding address locks in ascending lexicographic full-address order before acquiring `locks/index.lock`
- **AND THEN** the operation fails explicitly rather than partially committing delivery if it cannot obtain the required lock set within its bounded timeout

#### Scenario: Missing symlink target causes explicit delivery failure
- **WHEN** a sender attempts delivery to a mailbox address whose `mailboxes/<address>` symlink target is missing or invalid
- **THEN** the filesystem mailbox transport fails that delivery explicitly
- **AND THEN** the system does not silently create a replacement mailbox directory at an unintended path
