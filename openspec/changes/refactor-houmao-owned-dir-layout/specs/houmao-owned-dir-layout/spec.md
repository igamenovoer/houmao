## ADDED Requirements

### Requirement: Houmao-owned directories are split into fixed responsibility zones
The system SHALL separate Houmao-owned directories into distinct filesystem zones with different default locations and responsibilities.

The default per-user Houmao roots SHALL be:
- registry root: `~/.houmao/registry`
- runtime root: `~/.houmao/runtime`
- mailbox root: `~/.houmao/mailbox`

For each started session, the default per-agent job dir SHALL be derived under the selected working directory as:
- `<working-directory>/.houmao/jobs/<session-id>/`

Subsystem-specific explicit overrides that already exist MAY continue to relocate the effective registry root, runtime root, launcher home, or mailbox root. When no such override is supplied, the system SHALL use the defaults above.

#### Scenario: Default Houmao roots resolve under the user home
- **WHEN** a developer starts new Houmao-managed runtime or mailbox work without explicit root overrides
- **THEN** the system resolves the default registry, runtime, and mailbox roots under `~/.houmao/`

#### Scenario: Job dir is derived from working directory and session id
- **WHEN** the runtime starts a session with working directory `/repo/app` and generated session id `session-20260314-120000Z-abcd1234`
- **THEN** the default per-agent job dir for that session is `/repo/app/.houmao/jobs/session-20260314-120000Z-abcd1234/`

### Requirement: Houmao-owned zones keep discovery, durable state, shared mailbox state, and destructive scratch separate
The system SHALL preserve distinct mutability and ownership boundaries across the Houmao-owned zones.

At minimum:
- the registry root SHALL contain discovery-oriented metadata only,
- the runtime root SHALL contain durable Houmao-managed runtime and launcher state,
- the mailbox root SHALL contain shared mailbox transport state,
- the per-agent job dir SHALL contain session-local logs, outputs, temporary files, and destructive scratch work for one started session.

Mutable runtime session state, launcher-managed CAO home state, task-specific logs or outputs, and mailbox contents MUST NOT be relocated into the shared registry root as part of this directory model.

Mailbox state MUST remain independently relocatable and MUST NOT be implicitly nested under the runtime root or a per-agent job dir just because those other zones exist.

#### Scenario: Registry root is not used as mutable CAO or runtime storage
- **WHEN** the system publishes live-agent discovery metadata and also starts a launcher-managed CAO service
- **THEN** the shared registry contains only registry-owned discovery records
- **AND THEN** launcher-managed CAO home state and durable runtime session state are stored outside the registry root

#### Scenario: Job dir does not replace shared mailbox or durable runtime state
- **WHEN** a started session writes session-local scratch files while also using mailbox support and runtime-managed manifest persistence
- **THEN** scratch files and temporary outputs live under that session's per-agent job dir
- **AND THEN** mailbox content and durable runtime session state remain in their own independent zones
