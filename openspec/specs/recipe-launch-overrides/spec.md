# recipe-launch-overrides Specification

## Purpose
Define how presets and direct builds customize provider launch arguments and typed tool parameters. Specify layer precedence, adapter validation and projection, and the fields Houmao reserves to maintain backend control.
## Requirements
### Requirement: Structured launch overrides are available to recipes and direct builds
The system SHALL support an optional structured `launch_overrides` model for raw CLI argument overrides alongside a first-class per-tool `tool_params` mapping on presets and direct builds.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Raw argument overrides SHALL be available through declarative preset YAML at `launch.overrides.args` and direct build inputs at `BuildRequest.launch_overrides.args`. Per-tool settings SHALL be declared at top-level `tool_params` on presets and layered `tool_params` inputs on `BuildRequest` rather than nested under `launch.overrides.tool_params`. Both models SHALL remain secret-free and SHALL NOT embed credential values, tokens, or inline secrets.

#### Scenario: Recipe declares launch overrides
- **WHEN** a developer adds `launch.overrides.args` and top-level `tool_params` to a brain preset
- **THEN** the preset remains declarative and secret-free
- **AND THEN** preset loading exposes raw `args` overrides and per-tool `tool_params` to downstream build and runtime consumers

#### Scenario: Direct build uses the same launch-overrides model
- **WHEN** a developer constructs a brain through direct build inputs without using a preset
- **THEN** they can supply `BuildRequest.launch_overrides` for raw `args` and `BuildRequest.direct_tool_params` for per-tool settings
- **AND THEN** direct-build and preset-backed builds use one shared contract

#### Scenario: Legacy nested launch overrides tool_params is rejected
- **WHEN** a preset declares `launch.overrides.tool_params` instead of top-level `tool_params`
- **THEN** preset parsing fails explicitly before brain construction
- **AND THEN** the error directs the author to top-level `tool_params`

### Requirement: Launch overrides merge with tool-adapter defaults under explicit section precedence rules
The system SHALL treat tool-adapter launch data as the default base layer for the selected tool and SHALL merge raw `args` overrides and layered `tool_params` using explicit precedence rules.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

For `args`, `mode = append` SHALL append additional args after adapter defaults and `mode = replace` SHALL replace the adapter default arg list for the winning override section. When both preset and direct-build `args` overrides are present, `args` SHALL remain an atomic section where direct-build `args` replaces preset `args` before evaluating `mode` against adapter defaults, without discarding `tool_params` from any layer.

#### Scenario: Recipe appends args to adapter defaults
- **WHEN** the selected tool adapter declares default launch args
- **AND WHEN** a preset declares `launch.overrides.args.mode = append`
- **THEN** the effective preset-owned base arg list contains the adapter defaults followed by the preset-provided args

#### Scenario: Direct build args override does not drop recipe tool params
- **WHEN** a preset declares `tool_params.include_partial_messages = true`
- **AND WHEN** the direct build request declares only `launch_overrides.args`
- **THEN** the direct build request wins for the `args` section
- **AND THEN** the preset-owned `tool_params.include_partial_messages` value survives unchanged

#### Scenario: Direct build args section replaces recipe args section
- **WHEN** a preset declares `launch.overrides.args`
- **AND WHEN** the direct build request also declares `launch_overrides.args`
- **THEN** the direct build `args` section replaces the preset `args` section
- **AND THEN** the winning `args.mode` evaluates against adapter defaults rather than composing modes across layers

### Requirement: Backend-reserved protocol args are not recipe-overridable
The system SHALL reserve backend-protocol continuity and machine-readable control args to runtime-owned backend code.

Launch overrides SHALL NOT remove, replace, or contradict backend-reserved protocol args such as resume identifiers, machine-readable output-mode args, or other backend-owned control flags.

#### Scenario: Launch override conflicts with a reserved backend arg
- **WHEN** a launch-overrides request attempts to inject, remove, or contradict a backend-reserved protocol arg
- **THEN** the system fails explicitly before backend start
- **AND THEN** the error identifies that the rejected setting conflicts with runtime-owned backend behavior

### Requirement: Launch overrides expose no Gemini tool or backend scope
Recipe launch-override validation SHALL NOT recognize Gemini tool parameters or Gemini backend combinations.

#### Scenario: Gemini launch override is rejected as an unsupported tool
- **WHEN** a recipe or direct build supplies launch overrides for Gemini
- **THEN** validation rejects the tool rather than reporting a supported empty Gemini parameter set

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

The system SHALL resolve effective `tool_params` for a selected tool in strict precedence order: (1) `adapter.yaml` `launch.default_tool_params`, (2) the selected setup, (3) specialist or preset `tool_params`, (4) project profile or launch-profile `tool_params`, and (5) one-shot direct build or launch `tool_params`. The setup layer SHALL apply recognized explicit native permission keys followed by its optional `tool-params.yaml`.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

Merging SHALL preserve unspecified nested fields from lower layers while honoring explicit null overrides.

#### Scenario: Higher layer patches nested tool_params without erasing sibling fields
- **WHEN** a DSH specialist defines `tool_params.provider` and `tool_params.models`
- **AND WHEN** a launch profile supplies `tool_params` overriding only one nested field or MCP server list
- **THEN** effective `tool_params` retains the specialist's remaining `provider` and `models` fields alongside the profile override

#### Scenario: Selected setup supplies both native and typed permission configuration
- **WHEN** both a recognized native setup key and the setup's `tool-params.yaml` supply a value for the same configurable permission field
- **THEN** the setup's typed value takes precedence for that field
- **AND THEN** the values for other fields still follow their own layer precedence

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
