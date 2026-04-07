## ADDED Requirements

### Requirement: `houmao-mgr agents launch` supports explicit launch-profile-backed launch
`houmao-mgr agents launch` SHALL support selecting a reusable explicit launch profile through `--launch-profile <name>`.

`--launch-profile` and `--agents` SHALL be mutually exclusive.

When `--launch-profile` is used, the command SHALL:
- resolve the named explicit launch profile from the selected source project context,
- resolve the profile's referenced recipe source,
- derive the effective recipe and tool from that source before build,
- apply launch-profile defaults before direct CLI overrides.

`houmao-mgr agents launch` SHALL NOT consume easy `project easy profile` selections through `--launch-profile`.

When the resolved profile source already determines one exact tool family, the effective provider SHALL default from that resolved source.

If the operator supplies `--provider` together with `--launch-profile`, the system SHALL either accept the value when it matches the resolved profile source or fail clearly when it conflicts.

#### Scenario: Launch-profile-backed launch derives provider from the resolved recipe
- **WHEN** launch profile `alice` resolves to one Codex-backed recipe source
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile alice`
- **THEN** the command derives the effective provider from that resolved source
- **AND THEN** the operator does not need to restate the provider only to launch the stored profile

#### Scenario: Launch-profile selector conflicts with direct source selector
- **WHEN** an operator runs `houmao-mgr agents launch --launch-profile alice --agents gpu-kernel-coder`
- **THEN** the command fails clearly before build
- **AND THEN** it reports that `--launch-profile` and `--agents` cannot be combined

### Requirement: Launch-profile-backed launch applies profile defaults before direct CLI overrides
When `houmao-mgr agents launch` resolves an explicit launch profile, the effective launch or build specification SHALL be composed from:

1. source recipe defaults
2. launch-profile defaults
3. direct CLI overrides

At minimum, launch-profile-backed launch SHALL allow profile defaults to contribute:
- managed-agent name or id
- working directory
- auth override
- operator prompt-mode override
- durable env defaults
- declarative mailbox config

Direct CLI overrides such as `--agent-name`, `--agent-id`, `--auth`, and `--workdir` SHALL remain one-off overrides and SHALL NOT rewrite the stored launch profile.

#### Scenario: Launch-profile-backed launch uses stored managed-agent name when none is supplied
- **WHEN** launch profile `alice` stores default managed-agent name `alice`
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile alice`
- **THEN** the launch uses `alice` as the managed-agent logical name
- **AND THEN** the operator does not need to restate that name for each launch from the same profile

#### Scenario: Direct auth override wins over the launch-profile default
- **WHEN** launch profile `alice` stores auth override `alice-creds`
- **AND WHEN** an operator runs `houmao-mgr agents launch --launch-profile alice --auth breakglass`
- **THEN** the launch uses auth bundle `breakglass`
- **AND THEN** the stored launch profile still records `alice-creds` as its reusable default
