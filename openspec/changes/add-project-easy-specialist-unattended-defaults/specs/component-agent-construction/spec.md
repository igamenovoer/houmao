## MODIFIED Requirements

### Requirement: Agent preset schema is minimal and extensible

Agent presets SHALL include only fields required by current behavior: selected skills, optional default auth, optional launch settings, optional mailbox settings, and optional `extra`.

The system SHALL NOT require build-time `default_agent_name` or other duplicated identity fields in preset files.

If present, preset `launch` SHALL be an object containing optional `prompt_mode` and optional `overrides`. `launch.overrides`, when present, SHALL use the existing launch-overrides shape of optional `args` and optional `tool_params`.

Allowed `launch.prompt_mode` values SHALL be `unattended` and `as_is`.

Unknown top-level preset fields SHALL be rejected. Non-core extension data SHALL live under `extra` rather than through pre-allocated unused top-level schema fields.

#### Scenario: Minimal preset omits build-time identity fields

- **WHEN** a developer authors a preset for one role, tool, and setup
- **THEN** the preset MAY omit `name`, `role`, `tool`, and `default_agent_name`
- **AND THEN** the system SHALL still resolve the preset successfully from its path and required core fields

#### Scenario: Launch settings use one explicit schema

- **WHEN** a developer authors preset-owned launch behavior
- **THEN** `prompt_mode` SHALL appear under `launch.prompt_mode`
- **AND THEN** `launch.prompt_mode` SHALL use only `unattended` or `as_is`
- **AND THEN** any preset-owned launch overrides SHALL appear under `launch.overrides`
- **AND THEN** `launch.overrides` SHALL use only the supported `args` and `tool_params` sections

#### Scenario: Non-core preset extensions live under extra

- **WHEN** a consumer needs secret-free subsystem-specific preset metadata outside the core schema
- **THEN** that metadata SHALL be stored under `extra`
- **AND THEN** the core preset resolution path SHALL NOT depend on unsupported top-level extension fields
- **AND THEN** preserved gateway defaults, when needed for migrated blueprint behavior, SHALL live under `extra.gateway`

#### Scenario: Unknown top-level preset field fails validation

- **WHEN** a preset file declares an unsupported top-level field such as legacy `config_profile`
- **THEN** preset loading SHALL fail explicitly
- **AND THEN** the error SHALL direct authors toward the supported core fields and `extra`

### Requirement: Brain construction accepts operator prompt policy intent

The system SHALL let callers declare an operator prompt policy when constructing a brain, including a mode that requests unattended launch behavior where startup operator prompts are forbidden and a mode that leaves provider startup behavior untouched.

The selected policy SHALL be available through:

- declarative preset YAML at `launch.prompt_mode`
- direct build inputs at `BuildRequest.operator_prompt_mode`

Allowed values SHALL be `unattended` and `as_is`.

When callers omit prompt policy entirely, current brain construction flows SHALL resolve that omission to the unattended default rather than to pass-through startup behavior.

#### Scenario: Developer constructs a brain with unattended prompt policy

- **WHEN** a developer constructs a brain using direct inputs or a declarative preset that requests `launch.prompt_mode = unattended`
- **THEN** the construction input includes that requested launch policy alongside tool, skills, setup, and auth
- **AND THEN** the requested policy remains secret-free metadata that does not embed API keys, tokens, inline credential material, or credential file contents

#### Scenario: Developer constructs a brain with as-is prompt policy

- **WHEN** a developer constructs a brain using direct inputs or a declarative preset that requests `launch.prompt_mode = as_is`
- **THEN** the construction input includes that requested pass-through policy alongside tool, skills, setup, and auth
- **AND THEN** the requested policy remains secret-free metadata that does not embed API keys, tokens, inline credential material, or credential file contents

#### Scenario: Omitted prompt policy resolves to unattended during construction

- **WHEN** a developer constructs a brain without setting declarative or direct prompt policy
- **THEN** the construction flow resolves the effective prompt policy as unattended
- **AND THEN** downstream manifest and runtime launch consumers do not treat omission as pass-through behavior

### Requirement: Brain manifest persists unresolved launch policy intent

The system SHALL persist requested operator prompt policy in the resolved brain manifest as abstract launch intent rather than as pre-resolved provider-version-specific CLI flags or runtime state patches.

The resolved manifest SHALL store that request at `launch_policy.operator_prompt_mode`.

Allowed stored values SHALL be `unattended` and `as_is`.

#### Scenario: Manifest records unattended intent without provider-specific patch details

- **WHEN** a brain is constructed with `operator_prompt_mode = unattended`
- **THEN** the resolved brain manifest records that requested policy at `launch_policy.operator_prompt_mode`
- **AND THEN** the manifest does not treat version-resolved strategy ids, provider trust entries, or concrete injected CLI args as construction-time inputs

#### Scenario: Manifest records as-is intent without provider-specific patch details

- **WHEN** a brain is constructed with `operator_prompt_mode = as_is`
- **THEN** the resolved brain manifest records that requested policy at `launch_policy.operator_prompt_mode`
- **AND THEN** the manifest does not imply unattended launch-policy mutation for that session
