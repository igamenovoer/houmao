## ADDED Requirements

### Requirement: Unattended Kimi launches pre-seed provider workspace trust

When a managed Kimi Code launch resolves `operator_prompt_mode = unattended`, the runtime SHALL write the provider-native workspace-trust record for the launch working directory into the managed Kimi home before provider start, using the provider's deterministic record location and key derived from the launch working directory. Provider-start planning SHALL assert the record for the actual launch working directory before every fresh headless start, fresh TUI start, and relaunch, repairing a missing or drifted record.

The pre-seed SHALL be recorded in launch provenance with the record path, the derived workspace key, and the resulting state.

When a managed Kimi Code launch resolves `operator_prompt_mode = as_is`, the runtime SHALL NOT create or modify provider workspace-trust state.

#### Scenario: Unattended Kimi TUI starts without a trust modal
- **WHEN** Houmao launches a fresh managed Kimi 0.34.0-or-later TUI with `operator_prompt_mode = unattended` into a working directory the managed home has never seen
- **THEN** the managed home contains the workspace-trust record for that working directory before provider start
- **AND THEN** the TUI reaches the ready surface without displaying the trust-confirmation modal

#### Scenario: Unattended Kimi headless home is trusted before the first turn
- **WHEN** Houmao runs a managed Kimi headless turn with `operator_prompt_mode = unattended`
- **THEN** the workspace-trust record for the launch working directory exists in the managed home before provider start
- **AND THEN** project-level provider configuration that requires trust follows the trusted path

#### Scenario: Relaunch into a different working directory re-asserts trust
- **WHEN** a managed Kimi relaunch targets a working directory different from the one trusted at brain construction
- **THEN** provider-start planning writes the trust record for the relaunch working directory
- **AND THEN** launch provenance records the new workspace key

#### Scenario: Missing trust record is repaired at provider start
- **WHEN** the workspace-trust record was removed or altered between brain construction and an unattended provider start
- **THEN** provider-start planning restores the canonical record before the provider process launches

#### Scenario: As-is launch leaves trust state untouched
- **WHEN** Houmao launches a managed Kimi session with `operator_prompt_mode = as_is`
- **THEN** the runtime writes no workspace-trust record
- **AND THEN** the provider's native trust interaction is preserved for the operator
