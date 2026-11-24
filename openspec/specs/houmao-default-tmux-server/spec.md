# houmao-default-tmux-server Specification

## Purpose

Give Houmao launches a stable, owner-private tmux server address that they can share across projects and reuse after the server exits.

## Requirements

### Requirement: The shared registry records the Houmao default per execution owner

The owner’s effective shared registry SHALL store a versioned Houmao default record with the observed owner scope and an absolute socket path. The scope SHALL distinguish effective OS users and host or container socket domains. The record SHALL be independent of project identity, agent identity, and live presence leases.

#### Scenario: Two projects share an owner default

- **WHEN** launches from two projects select `houmao-default` in the same owner scope and registry
- **THEN** both use the same recorded absolute socket and create their own sessions there

#### Scenario: Registries without an initialized address converge for the same owner

- **WHEN** two launches in the same owner scope select `houmao-default` with separate, initially empty effective registry roots
- **THEN** each registry records the same owner-derived default address

#### Scenario: A shared registry sees distinct owner scopes

- **WHEN** two launches select `houmao-default` from distinct host or container socket domains or from distinct effective OS users
- **THEN** each resolves its own scoped record and socket address

### Requirement: The Houmao default starts lazily at its recorded address

On the first eligible launch, Houmao SHALL atomically publish the owner’s default socket under a short, owner-private socket directory before starting the first session. Later eligible launches SHALL use the recorded path, starting a server there when needed. Read-only operations and profile authoring SHALL leave the default uninitialized.

#### Scenario: Two initial launches race

- **WHEN** two launches in one owner scope concurrently select an uninitialized Houmao default
- **THEN** both use the same successfully published owner record
- **AND THEN** each successful launch creates its session on that server

#### Scenario: The recorded server is absent on the next launch

- **WHEN** the registry has a valid record and the default server has never started or has since exited
- **THEN** the next eligible launch starts its session at the recorded path

#### Scenario: The recorded address is unsafe or inaccessible

- **WHEN** launch finds a malformed or foreign record, an unsafe socket path, or a socket it cannot use
- **THEN** launch reports the problem with that selection and leaves other servers untouched
- **AND THEN** the existing record remains available for diagnosis

### Requirement: Agent cleanup preserves the Houmao default

Agent stop and cleanup SHALL act only on the verified target session and preserve the Houmao default record. The server SHALL follow normal tmux lifecycle when its last session exits.

#### Scenario: Stop preserves sibling sessions

- **WHEN** two agents use the Houmao default and an operator stops one of them
- **THEN** the other session and the default registry record remain available

#### Scenario: Registry cleanup removes expired agent presence

- **WHEN** registry cleanup removes stale agent presence from a registry that also holds a Houmao default record
- **THEN** cleanup leaves the Houmao default address available for later launches
