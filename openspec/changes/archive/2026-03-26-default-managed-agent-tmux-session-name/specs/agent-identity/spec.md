## ADDED Requirements

### Requirement: Runtime-owned tmux session names use canonical agent name and launch timestamp by default
For runtime-owned tmux-backed managed launches in the current managed-launch backend set, the system SHALL derive the default live tmux session handle from:

- the canonical managed-agent name in `AGENTSYS-<name>` form, and
- the launch timestamp expressed as Unix epoch milliseconds.

When the caller does not provide an explicit tmux session name, the default tmux session handle format SHALL be:

- `<canonical-agent-name>-<epoch-ms>`

The generated timestamp suffix SHALL use epoch time down to milliseconds at the moment the default tmux session name is chosen.

If the generated default tmux session name is already occupied by another live tmux session, session start SHALL fail explicitly. The system SHALL NOT mutate the generated candidate by extending a suffix, appending randomness, or retrying with an alternate default handle inside the same launch attempt.

When the caller provides an explicit tmux session name such as `--session-name`, the system SHALL use that explicit value instead of the timestamp-based default.

The system SHALL continue to treat the resulting tmux session name as an opaque transport handle. The purpose of this handle is limited to avoiding collisions with irrelevant tmux sessions and making Houmao-owned tmux sessions recognizable to operators.

Runtime discovery and control SHALL rely on persisted shared-registry or manifest metadata rather than reverse-parsing canonical agent identity or timestamp components from that tmux session name string.

The system SHALL NOT use raw tmux session listing plus tmux-name parsing as the contract for managed-agent listing, agent-name-to-session mapping, or related discovery behaviors that already belong to the shared registry.

#### Scenario: Default runtime-owned tmux handle uses canonical name plus epoch milliseconds
- **WHEN** the runtime starts a tmux-backed managed session with canonical agent name `AGENTSYS-james`
- **AND WHEN** the caller does not provide an explicit tmux session name
- **AND WHEN** the chosen launch timestamp is `1760000123456`
- **AND WHEN** no live tmux session already occupies `AGENTSYS-james-1760000123456`
- **THEN** the live tmux session name is `AGENTSYS-james-1760000123456`

#### Scenario: Explicit tmux session-name override bypasses the default generator
- **WHEN** the runtime starts a tmux-backed managed session with canonical agent name `AGENTSYS-james`
- **AND WHEN** the caller explicitly provides tmux session name `custom-james`
- **THEN** the live tmux session name is `custom-james`
- **AND THEN** the runtime does not replace it with an `AGENTSYS-james-<epoch-ms>` default

#### Scenario: Generated default-name collision fails explicitly
- **WHEN** the runtime starts a tmux-backed managed session with canonical agent name `AGENTSYS-james`
- **AND WHEN** the caller does not provide an explicit tmux session name
- **AND WHEN** the chosen launch timestamp is `1760000123456`
- **AND WHEN** live tmux session `AGENTSYS-james-1760000123456` already exists
- **THEN** session start fails with an explicit tmux-session-name conflict error
- **AND THEN** the runtime does not generate a mutated fallback name

#### Scenario: Discovery does not reverse-parse the timestamp-based tmux handle
- **WHEN** a managed session persists tmux session name `AGENTSYS-james-1760000123456`
- **THEN** the system treats that tmux session name as an opaque transport handle
- **AND THEN** managed-agent listing or agent-name-to-session mapping continues to resolve through shared-registry or manifest metadata rather than tmux-name parsing

## MODIFIED Requirements

### Requirement: User-provided agent names are validated and MUST NOT contain a standalone `AGENTSYS` token
The system SHALL validate the user-provided agent name portion for tmux-backed managed launches using a conservative character set that is safe for both tmux session names and Unix-style filenames.

Allowed characters for the user-provided agent name portion are:
- ASCII letters `A-Z` and `a-z`,
- ASCII digits `0-9`,
- underscore (`_`) and hyphen (`-`).

The user-provided agent name portion MUST start with an ASCII letter or digit.
The system SHALL NOT enforce an additional length limit on the user-provided agent name portion beyond tmux constraints.

Additionally, the user-provided agent name portion MUST NOT begin with a case-insensitive `AGENTSYS` token immediately followed by a non-alphanumeric separator.

This reserved-prefix rejection applies only at the beginning of the user-provided agent name portion. Later occurrences of `AGENTSYS`, and substring occurrences inside a larger alphanumeric run, are allowed.

This validation SHALL be applied before the runtime canonicalizes the managed-agent name into `AGENTSYS-<name>` form.

#### Scenario: Exact uppercase reserved prefix with hyphen is rejected
- **WHEN** a caller provides managed-agent name `AGENTSYS-james`
- **THEN** the system rejects the operation with an explicit reserved-prefix error

#### Scenario: Lowercase reserved prefix with hyphen is rejected
- **WHEN** a caller provides managed-agent name `agentsys-james`
- **THEN** the system rejects the operation with an explicit reserved-prefix error

#### Scenario: Reserved prefix with underscore separator is rejected
- **WHEN** a caller provides managed-agent name `AGENTSYS_james`
- **THEN** the system rejects the operation with an explicit reserved-prefix error

#### Scenario: Split spelling is allowed
- **WHEN** a caller provides managed-agent name `AGENT-SYS-james`
- **THEN** the system accepts the name

#### Scenario: Later standalone token is allowed
- **WHEN** a caller provides managed-agent name `james-AGENTSYS`
- **THEN** the system accepts the name

#### Scenario: Alphanumeric extension is allowed
- **WHEN** a caller provides managed-agent name `AGENTSYS123`
- **THEN** the system accepts the name

## REMOVED Requirements

### Requirement: Runtime-owned tmux session names combine canonical agent name and authoritative agent-id prefix
**Reason**: The default tmux session naming contract now uses canonical managed-agent name plus launch-time epoch milliseconds instead of an `agent_id` prefix.
**Migration**: Update runtime code, tests, and documentation to expect `<canonical-agent-name>-<epoch-ms>` as the default when no explicit tmux session name is provided, and treat default-name collisions as explicit launch errors.
