# recipe-launch-overrides Specification

## MODIFIED Requirements

### Requirement: Structured launch overrides are available to recipes and direct builds
The system SHALL support an optional structured `launch_overrides` model for raw CLI argument overrides alongside a first-class per-tool `tool_params` mapping on presets and direct builds.

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

## REMOVED Requirements

### Requirement: Tool-specific launch params are declarative, shared-validated, and backend-scoped
**Reason**: The boolean-only `launch.metadata.tool_params` YAML projection DSL in `adapter.yaml` cannot express nested per-tool configuration, home-file synthesis, or tool-specific merge semantics needed across Claude, Codex, Kimi, and DSH.
**Migration**: Define per-tool schemas and home/launch materialization in each tool's registered adapter and author `tool_params` directly on `adapter.yaml` `launch.default_tool_params`, `<setup>/tool-params.yaml`, specialists, presets, profiles, or direct launches.

## ADDED Requirements

### Requirement: Per-tool parameters are validated and applied by tool-owned adapters

Each supported tool (`claude`, `codex`, `kimi`, `dsh`) SHALL validate `tool_params` against its own strict schema and apply effective `tool_params` through tool-owned home materialization and backend-scoped launch preparation without a `launch.metadata.tool_params` YAML DSL in `adapter.yaml`. Claude SHALL support boolean `include_partial_messages` for `claude_headless`, and unknown keys, inline secrets, or unsupported backend combinations SHALL fail explicitly.

#### Scenario: Supported Claude tool param validates and projects for headless
- **WHEN** a Claude preset or profile declares `tool_params.include_partial_messages = true`
- **THEN** validation accepts that parameter for the `claude` tool family
- **AND THEN** `claude_headless` launch resolution includes `--include-partial-messages`

#### Scenario: Tool adapter YAML projection metadata is rejected
- **WHEN** a `tools/<tool>/adapter.yaml` file declares legacy `launch.metadata.tool_params` projection rules
- **THEN** tool-adapter parsing fails explicitly rather than ignoring the legacy DSL

#### Scenario: Unsupported tool param or backend combination is rejected
- **WHEN** a `tool_params` layer contains an unknown key for the selected tool or a parameter unsupported by the resolved backend
- **THEN** validation or launch resolution fails explicitly before provider startup
- **AND THEN** it does not silently keep or ignore that unsupported setting

### Requirement: Per-tool parameters compose across five configuration layers

The system SHALL resolve effective `tool_params` for a selected tool in strict precedence order: (1) `adapter.yaml` `launch.default_tool_params`, (2) optional `<setup>/tool-params.yaml`, (3) specialist or preset `tool_params`, (4) project profile or launch-profile `tool_params`, and (5) one-shot direct build or launch `tool_params`. Merging SHALL preserve unspecified nested fields from lower layers while honoring explicit null overrides.

#### Scenario: Higher layer patches nested tool_params without erasing sibling fields
- **WHEN** a DSH specialist defines `tool_params.provider` and `tool_params.models`
- **AND WHEN** a launch profile supplies `tool_params` overriding only one nested field or MCP server list
- **THEN** effective `tool_params` retains the specialist's remaining `provider` and `models` fields alongside the profile override
