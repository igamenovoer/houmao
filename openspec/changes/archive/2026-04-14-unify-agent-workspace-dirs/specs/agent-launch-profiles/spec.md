## REMOVED Requirements

### Requirement: Launch profiles may store optional memory-directory intent
**Reason**: Replaced by optional persist-lane intent.
**Migration**: None. Backward compatibility and migration are explicitly out of scope for this change.

### Requirement: Launch-profile memory-directory intent participates in launch precedence
**Reason**: Replaced by persist-lane launch precedence.
**Migration**: None. Backward compatibility and migration are explicitly out of scope for this change.

## ADDED Requirements

### Requirement: Launch profiles may store optional persist-lane intent
Launch profiles SHALL be able to store optional persist-lane intent as one of:

- inherited persist binding,
- exact persist directory,
- disabled persist binding.

Launch profiles SHALL NOT store `memory_dir` or memory-disabled fields as the current contract.

#### Scenario: Launch profile stores exact persist directory
- **WHEN** an operator creates launch profile `alice` with `--persist-dir /shared/alice`
- **THEN** the launch profile records exact persist-lane intent for `/shared/alice`
- **AND THEN** later launches from `alice` use that value unless directly overridden

#### Scenario: Launch profile stores disabled persistence
- **WHEN** an operator creates launch profile `alice` with `--no-persist-dir`
- **THEN** the launch profile records disabled persist-lane intent
- **AND THEN** later launches from `alice` do not create a persist lane unless directly overridden

### Requirement: Launch-profile persist-lane intent participates in launch precedence
Direct `--persist-dir <path>` SHALL override profile-owned disabled persist binding or profile-owned exact persist binding.

Direct `--no-persist-dir` SHALL override any profile-owned persist configuration.

When no direct persist override is supplied, the selected launch profile's persist intent SHALL apply.

#### Scenario: Direct persist-dir overrides stored disabled persistence
- **WHEN** launch profile `alice` stores disabled persist binding
- **AND WHEN** an operator launches from `alice` with `--persist-dir /tmp/alice-persist`
- **THEN** the launch resolves persist directory `/tmp/alice-persist`
- **AND THEN** the stored profile still records disabled persist binding

#### Scenario: Stored exact persist applies without direct override
- **WHEN** launch profile `alice` stores persist directory `/shared/alice`
- **AND WHEN** an operator launches from `alice` without `--persist-dir` or `--no-persist-dir`
- **THEN** the launch resolves persist directory `/shared/alice`
