## ADDED Requirements

### Requirement: Brain construction accepts a structured launch-overrides contract
The system SHALL let callers declare secret-free launch-override intent as part of normal brain construction inputs instead of limiting recipe-backed builds to tool-adapter launch defaults.

That construction input SHALL be available through:

- declarative recipe YAML at `launch_overrides`
- direct build inputs at `BuildRequest.launch_overrides`

The supported construction-time launch-overrides model SHALL include at minimum:

- an `args` section with explicit merge behavior against tool-adapter defaults
- a `tool_params` section for typed, tool-specific launch settings

#### Scenario: Recipe construction includes launch-overrides intent
- **WHEN** a developer constructs a brain from a recipe that declares `launch_overrides`
- **THEN** the selected tool, skills, config profile, credential profile, and launch-overrides request are all part of the construction input contract
- **AND THEN** the recipe remains declarative and secret-free

#### Scenario: Direct build input uses the same structured launch-overrides model
- **WHEN** a developer constructs a brain without a recipe and supplies `BuildRequest.launch_overrides`
- **THEN** the direct-build path accepts the same structured launch-overrides model used by recipes
- **AND THEN** the system does not require a separate ad hoc launch-arg-only override path for parity

### Requirement: Brain manifests persist adapter defaults and requested launch overrides separately
The system SHALL persist launch-override state in the resolved brain manifest as structured data with separate fields for adapter-owned launch defaults and caller-requested launch overrides.

The resolved brain manifest SHALL store enough non-secret information to explain:

- which launch defaults came from the selected tool adapter
- which launch overrides were requested by the recipe or direct build input
- which parts of the launch contract still require runtime resolution because backend applicability is selected later

The manifest MUST NOT embed credential material, inline secrets, backend-resolved effective args, or backend-reserved runtime continuity values as recipe-owned launch overrides.

#### Scenario: Manifest records defaults and requested override without flattening them together
- **WHEN** a brain is constructed from a recipe whose selected tool adapter has launch defaults and whose recipe also declares `launch_overrides`
- **THEN** the resolved manifest records the adapter defaults snapshot separately from the requested launch-overrides payload
- **AND THEN** audit or debugging consumers can distinguish reusable defaults from recipe-owned launch intent

#### Scenario: Manifest keeps backend applicability unresolved at build time
- **WHEN** a brain is constructed before a specific runtime backend has been chosen
- **THEN** the resolved manifest stores the requested launch-overrides contract as unresolved launch intent
- **AND THEN** the builder does not write backend-resolved effective args or mark every requested launch field as universally supported across later runtime backends

### Requirement: New builder output uses manifest schema version 2 for launch overrides
Brain construction that supports the launch-overrides contract SHALL write resolved brain manifests with `schema_version = 2`.

New builder output for this contract SHALL NOT continue writing the legacy schema-version-1 manifest layout as though it were equivalent.

#### Scenario: Builder writes schema version 2 manifest for launch-overrides-capable output
- **WHEN** a developer constructs a brain using a builder that supports `launch_overrides`
- **THEN** the resolved brain manifest is written with `schema_version = 2`
- **AND THEN** the manifest carries the structured launch-overrides contract rather than relying on the old v1 launch-args-only layout
