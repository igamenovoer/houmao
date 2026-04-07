## ADDED Requirements

### Requirement: Build and launch resolution applies launch-profile defaults between recipe defaults and direct overrides
When a launch is started from a reusable launch profile, the build and runtime pipeline SHALL resolve effective launch inputs by applying launch-profile defaults after source recipe defaults and before direct launch-time overrides.

At minimum, the pipeline SHALL allow launch-profile-derived values to influence:
- effective auth selection
- operator prompt-mode intent
- durable non-secret env records
- declarative mailbox configuration
- managed-agent identity defaults
- launch provenance

The resulting build manifest or runtime launch metadata SHALL preserve profile provenance in a secret-free form sufficient for inspection and replay, including whether the birth-time config came from an easy profile or an explicit launch profile.

#### Scenario: Launch-profile-derived auth and mailbox defaults survive into build and runtime resolution
- **WHEN** a launch profile stores auth override `alice-creds` and declarative mailbox defaults
- **AND WHEN** a managed-agent launch is started from that profile without conflicting direct overrides
- **THEN** brain construction uses `alice-creds` as the effective auth selection
- **AND THEN** the resulting launch pipeline carries the profile-derived mailbox configuration into runtime launch resolution

#### Scenario: Direct launch override still wins over launch-profile-owned workdir
- **WHEN** a launch profile stores working directory `/repos/alice`
- **AND WHEN** the operator launches from that profile with direct workdir override `/tmp/debug`
- **THEN** runtime launch uses `/tmp/debug` as the effective working directory
- **AND THEN** profile provenance still records that the launch originated from the named profile

### Requirement: Launch-profile prompt overlays are composed before backend-specific role injection
When a launch profile defines a prompt overlay, the system SHALL derive one effective role prompt before backend-specific role injection planning begins.

For `append`, the effective role prompt SHALL be the source role prompt followed by the profile overlay text.

For `replace`, the effective role prompt SHALL be the profile overlay text instead of the source role prompt.

The runtime SHALL treat that composed prompt as the role prompt for backend-specific role injection and SHALL NOT reapply the overlay as a separate second bootstrap step on resumed turns.

#### Scenario: Append overlay becomes part of the effective role prompt
- **WHEN** the source role prompt says `You are a CUDA programmer.`
- **AND WHEN** the selected launch profile stores prompt overlay mode `append` with text `Prefer Alice's repository conventions.`
- **THEN** the effective role prompt includes both the source role prompt and the appended profile text before role injection is planned
- **AND THEN** the runtime does not submit the overlay as an unrelated extra prompt after startup

#### Scenario: Replace overlay substitutes for the source role prompt
- **WHEN** the selected launch profile stores prompt overlay mode `replace`
- **THEN** the effective role prompt used for runtime role injection is the profile-owned overlay text
- **AND THEN** the runtime does not also inject the original source role prompt for that launch
