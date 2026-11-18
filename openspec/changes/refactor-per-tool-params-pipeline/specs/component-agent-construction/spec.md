# component-agent-construction Specification

## MODIFIED Requirements

### Requirement: Brain construction accepts a structured launch-overrides contract

The system SHALL let callers declare secret-free raw argument overrides (`launch_overrides.args`) and layered per-tool settings (`tool_params`) as part of normal brain construction inputs instead of limiting preset-backed builds to tool-adapter defaults.

Raw argument overrides SHALL be available through declarative preset YAML at `launch.overrides` and `BuildRequest.launch_overrides`. Per-tool settings SHALL be available across `adapter.yaml` `launch.default_tool_params`, optional `<setup>/tool-params.yaml`, preset `tool_params`, launch-profile `tool_params`, and direct build `tool_params`.

#### Scenario: Preset construction includes launch-overrides intent
- **WHEN** a developer constructs a brain from a preset that declares `launch.overrides` and `tool_params`
- **THEN** the selected tool, skills, setup, auth, raw `args` overrides, and `tool_params` are all part of the construction input contract
- **AND THEN** the preset remains declarative and secret-free

#### Scenario: Direct build input uses the same structured launch-overrides model
- **WHEN** a developer constructs a brain without a preset and supplies `BuildRequest.launch_overrides` and `BuildRequest.direct_tool_params`
- **THEN** the direct-build path accepts the same structured models used by presets and profiles
- **AND THEN** the system does not require a separate ad hoc override path for parity

### Requirement: Brain manifests persist adapter defaults and requested launch overrides separately

The system SHALL persist raw `launch_overrides` state and layered `tool_params` state in the resolved brain manifest as structured, secret-free data with separate provenance for defaults, caller-supplied layers, and merged effective `tool_params`.

The resolved brain manifest SHALL explain which defaults came from the tool adapter or setup, which overrides came from the preset, launch profile, or direct build input, and which merged `tool_params` were materialized into the home while deferring backend-specific CLI argument translation until runtime backend selection. The manifest MUST NOT embed credential material, inline secrets, backend-resolved effective args, or backend-reserved continuity flags.

#### Scenario: Manifest records defaults and requested override without flattening them together
- **WHEN** a brain is constructed from a preset whose selected tool adapter or setup has defaults and whose preset or profile also declares `launch.overrides` or `tool_params`
- **THEN** the resolved manifest records adapter/setup defaults separately from preset, profile, and direct overrides alongside merged effective `tool_params`
- **AND THEN** audit or debugging consumers can distinguish reusable defaults from caller-owned launch intent

#### Scenario: Manifest keeps backend applicability unresolved at build time
- **WHEN** a brain is constructed before a specific runtime backend has been chosen
- **THEN** the resolved manifest stores `launch_overrides` and effective `tool_params` without writing backend-resolved CLI args
- **AND THEN** runtime launch planning validates and projects backend-specific `tool_params` behavior once the backend is selected

## ADDED Requirements

### Requirement: Brain construction resolves per-tool parameters and materializes tool-owned home state

The construction pipeline SHALL validate each `tool_params` layer against the selected tool's partial schema and merge all layers into the tool's effective schema before materialization. For managed launches, the builder SHALL use the layers and effective configuration accepted by launch preflight. For direct builds, construction SHALL resolve those layers before materializing tool-owned home files, baseline model defaults, and setup-referenced credential environment allowlists.

#### Scenario: Invalid partial tool_params fails before writing manifest
- **WHEN** any `tool_params` layer contains an unknown field or invalid value for the selected tool
- **THEN** brain construction fails with an actionable validation diagnostic naming the source layer and field while omitting the input value
- **AND THEN** no resolved brain manifest is published for the failed build

### Requirement: DSH MCP configuration persists credential references

DSH MCP header and environment entries SHALL store a name and an `env_ref` to the selected private credential bundle. Catalog, YAML, manifest, and generated home state SHALL persist references. Houmao SHALL resolve each value into its declared MCP entry for the native invocation. Validation SHALL name fields and omit raw input values.

#### Scenario: Credential references survive a build and resolve privately
- **WHEN** a DSH source declares MCP header or environment references and the selected bundle contains their values
- **THEN** the persisted layers and materialized home configuration contain references and the native invocation receives the referenced values in the declared MCP entries
- **AND THEN** credential inspection omits the referenced values and an unrelated bundle update preserves them

#### Scenario: Literal or missing MCP credentials fail safely
- **WHEN** an authored layer contains a literal MCP header or environment value, or a managed launch cannot resolve an MCP reference in its selected credential bundle
- **THEN** validation rejects the layer before persistence or rejects the launch before runtime mutation, respectively
- **AND THEN** the resulting diagnostic identifies the field without including the literal value or other raw input
