# Spec Delta

## ADDED Requirements

### Requirement: Authored tool parameters take precedence over launch defaults

Houmao SHALL use the winning authored value for a supported tool parameter and fill omitted fields from the applicable launch defaults. A supported explicit null, false, or empty value SHALL retain its schema-defined meaning. Native projections SHALL use the resolved value and preserve the authored input.

#### Scenario: An inherited explicit value replaces an unattended default

- **WHEN** a tool setup sets a supported sandbox value and the specialist, profile, and one-shot inputs omit that field
- **THEN** the setup's value reaches the native agent
- **AND THEN** an omitted approval field receives the applicable launch default

#### Scenario: An explicit false differs from omission

- **WHEN** a supported boolean parameter defaults to true and a user explicitly supplies false at a winning layer
- **THEN** the effective and projected native value is false

#### Scenario: A direct input overrides an inherited native value

- **WHEN** the selected setup supplies a recognized native permission value and the one-shot tool parameters supply another supported value for that field
- **THEN** the one-shot value reaches the native agent
- **AND THEN** the authored setup and stored definitions retain their values

### Requirement: Reserved tool parameters reject authored input

Houmao SHALL reserve only fields it must derive to maintain the selected managed backend's control contract. An authored value for a reserved field SHALL fail validation even when it matches the derived value or is null. The error SHALL identify the field and reason and identify the supported Houmao control when one exists.

#### Scenario: A matching value still conflicts with runtime ownership

- **WHEN** a user supplies the backend-reserved machine-readable output setting with the exact value that Houmao would derive
- **THEN** validation rejects the setting before changing a runtime or invoking the provider
- **AND THEN** a higher-priority layer does not conceal the reserved input in a selected lower layer

#### Scenario: A supplied identity would replace the managed session binding

- **WHEN** a user attempts to set the native session identifier through a tool parameter or an equivalent authored native override
- **THEN** the error names the field and directs the user to the supported Houmao continuation selector

#### Scenario: A DSH setting would assume ownership of activation timing

- **WHEN** a managed DSH tool parameter layer supplies `hmr` with any value
- **THEN** validation reports that managed DSH reserves the startup and refresh boundary
- **AND THEN** the launch leaves the previous managed instance intact

## MODIFIED Requirements

### Requirement: Per-tool parameters are validated and applied by tool-owned adapters

Each supported tool (`claude`, `codex`, `kimi`, `dsh`) SHALL validate `tool_params` against its own strict schema and apply effective `tool_params` through tool-owned home materialization and backend-scoped launch preparation without a `launch.metadata.tool_params` YAML DSL in `adapter.yaml`. Claude SHALL support boolean `include_partial_messages` for `claude_headless`, and unknown keys, inline secrets, or unsupported backend combinations SHALL fail explicitly.

#### Scenario: Supported Claude tool param validates and projects for headless
- **WHEN** a Claude preset or profile declares `tool_params.include_partial_messages = true`
- **THEN** validation accepts that parameter for the `claude` tool family
- **AND THEN** `claude_headless` launch resolution includes `--include-partial-messages`

#### Scenario: Tool adapter YAML projection metadata is rejected
- **WHEN** a tool-adapter file declares legacy `launch.metadata.tool_params` projection rules
- **THEN** tool-adapter parsing fails explicitly

#### Scenario: Unsupported tool param or backend combination is rejected
- **WHEN** a `tool_params` layer contains an unknown key for the selected tool or an effective parameter unsupported by the resolved backend
- **THEN** validation or launch resolution identifies the setting and unsupported combination before provider startup or takeover of an existing runtime

### Requirement: Per-tool parameters compose across five configuration layers

The system SHALL resolve effective `tool_params` for a selected tool in strict precedence order: (1) `adapter.yaml` `launch.default_tool_params`, (2) the selected setup, (3) specialist or preset `tool_params`, (4) project profile or launch-profile `tool_params`, and (5) one-shot direct build or launch `tool_params`. The setup layer SHALL apply recognized explicit native permission keys followed by its optional `tool-params.yaml`. Merging SHALL preserve unspecified nested fields from lower layers while honoring explicit null overrides.

#### Scenario: Higher layer patches nested tool_params without erasing sibling fields
- **WHEN** a DSH specialist defines `tool_params.provider` and `tool_params.models`
- **AND WHEN** a launch profile supplies `tool_params` overriding only one nested field or MCP server list
- **THEN** effective `tool_params` retains the specialist's remaining `provider` and `models` fields alongside the profile override

#### Scenario: Selected setup supplies both native and typed permission configuration
- **WHEN** both a recognized native setup key and the setup's `tool-params.yaml` supply a value for the same configurable permission field
- **THEN** the setup's typed value takes precedence for that field
- **AND THEN** the values for other fields still follow their own layer precedence
