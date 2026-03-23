## ADDED Requirements

### Requirement: Brain construction accepts a structured launch-surface contract
The system SHALL let callers declare secret-free launch-surface intent as part of normal brain construction inputs instead of limiting recipe-backed builds to tool-adapter launch defaults.

That construction input SHALL be available through:

- declarative recipe YAML at `launch_surface`
- direct build inputs at `BuildRequest.launch_surface_override`

The supported construction-time launch-surface model SHALL include at minimum:

- an `args` section with explicit merge behavior against tool-adapter defaults
- a `tool_params` section for typed, tool-specific launch settings

#### Scenario: Recipe construction includes launch-surface intent
- **WHEN** a developer constructs a brain from a recipe that declares `launch_surface`
- **THEN** the selected tool, skills, config profile, credential profile, and launch-surface request are all part of the construction input contract
- **AND THEN** the recipe remains declarative and secret-free

#### Scenario: Direct build input uses the same structured launch-surface model
- **WHEN** a developer constructs a brain without a recipe and supplies `BuildRequest.launch_surface_override`
- **THEN** the direct-build path accepts the same structured launch-surface model used by recipes
- **AND THEN** the system does not require a separate ad hoc launch-arg-only override path for parity

### Requirement: Brain manifests persist adapter defaults and requested launch overrides separately
The system SHALL persist launch-surface state in the resolved brain manifest as structured data with separate fields for adapter-owned launch defaults and caller-requested launch overrides.

The resolved brain manifest SHALL store enough non-secret information to explain:

- which launch-surface defaults came from the selected tool adapter
- which launch-surface overrides were requested by the recipe or direct build input
- which parts of the launch surface still require runtime resolution because backend applicability is selected later

The manifest MUST NOT embed credential material, inline secrets, or backend-reserved runtime continuity values as recipe-owned launch overrides.

#### Scenario: Manifest records defaults and requested override without flattening them together
- **WHEN** a brain is constructed from a recipe whose selected tool adapter has launch defaults and whose recipe also declares `launch_surface`
- **THEN** the resolved manifest records the adapter defaults snapshot separately from the requested launch-surface override
- **AND THEN** audit or debugging consumers can distinguish reusable defaults from recipe-owned launch intent

#### Scenario: Manifest keeps backend applicability unresolved at build time
- **WHEN** a brain is constructed before a specific runtime backend has been chosen
- **THEN** the resolved manifest stores the requested launch-surface contract as unresolved launch intent
- **AND THEN** the builder does not falsely mark every requested launch-surface field as universally supported across all later runtime backends
