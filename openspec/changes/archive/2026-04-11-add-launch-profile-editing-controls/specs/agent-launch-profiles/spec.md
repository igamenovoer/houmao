## ADDED Requirements

### Requirement: Launch profiles support explicit stored mutation modes
The shared launch-profile model SHALL distinguish stored profile mutation from one-shot launch overrides.

A patch mutation SHALL update only requested stored fields and preserve unspecified stored fields.

A replacement mutation SHALL write one complete new stored profile definition for the same profile name and lane, clearing omitted optional fields back to their create defaults.

Neither patch nor replacement mutation SHALL create, stop, relaunch, or rewrite any existing live managed-agent instance.

#### Scenario: Patch preserves unspecified launch-profile defaults
- **WHEN** launch profile `alice` stores workdir `/repos/alice`, mailbox config, and prompt overlay text
- **AND WHEN** an operator patches `alice` to update only the workdir to `/repos/alice-next`
- **THEN** the stored profile records workdir `/repos/alice-next`
- **AND THEN** the stored profile still records the prior mailbox config and prompt overlay text

#### Scenario: Replacement clears omitted optional launch-profile defaults
- **WHEN** launch profile `alice` stores workdir `/repos/alice`, mailbox config, and prompt overlay text
- **AND WHEN** an operator replaces `alice` in the same profile lane while supplying only the required source and workdir `/repos/alice-next`
- **THEN** the stored profile records workdir `/repos/alice-next`
- **AND THEN** the stored profile no longer records the prior mailbox config or prompt overlay text

#### Scenario: Stored mutation does not alter live instances
- **WHEN** managed-agent instance `alice-1` was launched from launch profile `alice`
- **AND WHEN** an operator patches or replaces stored launch profile `alice`
- **THEN** the stored reusable profile is updated for future launches
- **AND THEN** live instance `alice-1` and its existing runtime manifest remain unchanged by that stored-profile mutation

### Requirement: Launch-profile replacement preserves profile lane boundaries
The shared launch-profile authoring surfaces SHALL NOT allow replacement across the easy-profile and explicit-launch-profile lanes.

When a same-name profile exists in a different lane from the requested authoring surface, replacement SHALL fail clearly before updating the stored profile.

#### Scenario: Easy replacement cannot replace explicit launch profile
- **WHEN** explicit launch profile `alice` already exists
- **AND WHEN** an operator requests same-name easy-profile replacement for `alice`
- **THEN** the replacement fails clearly because `alice` is not an easy profile
- **AND THEN** the existing explicit launch profile remains unchanged

#### Scenario: Explicit replacement cannot replace easy profile
- **WHEN** easy profile `alice` already exists
- **AND WHEN** an operator requests same-name explicit launch-profile replacement for `alice`
- **THEN** the replacement fails clearly because `alice` is not an explicit launch profile
- **AND THEN** the existing easy profile remains unchanged
