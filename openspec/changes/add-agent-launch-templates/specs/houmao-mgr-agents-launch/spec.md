## ADDED Requirements

### Requirement: `houmao-mgr agents launch` supports template-backed launch
`houmao-mgr agents launch` SHALL support selecting a reusable launch template through `--template <name>`.

`--template` and `--agents` SHALL be mutually exclusive.

When `--template` is used, the command SHALL:
- resolve the named launch template from the selected source project context,
- resolve the template's referenced specialist or recipe source,
- derive the effective recipe and tool from that source before build,
- apply template defaults before direct CLI overrides.

When the resolved template source already determines one exact tool family, the effective provider SHALL default from that resolved source.

If the operator supplies `--provider` together with `--template`, the system SHALL either accept the value when it matches the resolved template source or fail clearly when it conflicts.

#### Scenario: Template-backed launch derives provider from the resolved source
- **WHEN** launch template `alice` resolves to one Codex-backed recipe source
- **AND WHEN** an operator runs `houmao-mgr agents launch --template alice`
- **THEN** the command derives the effective provider from that resolved source
- **AND THEN** the operator does not need to restate the provider only to launch the stored template

#### Scenario: Template selector conflicts with direct source selector
- **WHEN** an operator runs `houmao-mgr agents launch --template alice --agents gpu-kernel-coder`
- **THEN** the command fails clearly before build
- **AND THEN** it reports that `--template` and `--agents` cannot be combined

### Requirement: Template-backed launch applies template defaults before direct CLI overrides
When `houmao-mgr agents launch` resolves a launch template, the effective launch/build specification SHALL be composed from:

1. source recipe defaults
2. launch-template defaults
3. direct CLI overrides

At minimum, template-backed launch SHALL allow template defaults to contribute:
- managed-agent name or id
- working directory
- auth override
- operator prompt-mode override
- durable env defaults
- declarative mailbox config

Direct CLI overrides such as `--agent-name`, `--agent-id`, `--auth`, and `--workdir` SHALL remain one-off overrides and SHALL NOT rewrite the stored launch template.

#### Scenario: Template-backed launch uses stored managed-agent name when none is supplied
- **WHEN** launch template `alice` stores default managed-agent name `alice`
- **AND WHEN** an operator runs `houmao-mgr agents launch --template alice`
- **THEN** the launch uses `alice` as the managed-agent logical name
- **AND THEN** the operator does not need to restate that name for each launch from the same template

#### Scenario: Direct auth override wins over the template default
- **WHEN** launch template `alice` stores auth override `alice-creds`
- **AND WHEN** an operator runs `houmao-mgr agents launch --template alice --auth breakglass`
- **THEN** the launch uses auth bundle `breakglass`
- **AND THEN** the stored launch template still records `alice-creds` as its reusable default
