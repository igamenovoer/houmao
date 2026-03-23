## ADDED Requirements

### Requirement: Structured launch-surface overrides are available to recipes and direct builds
The system SHALL support an optional structured `launch_surface` override model for per-brain tool-launch behavior.

That model SHALL be available through:

- declarative recipe YAML at `launch_surface`
- direct build inputs at `BuildRequest.launch_surface_override`

The model SHALL support at minimum:

- an `args` section for raw CLI argument override behavior
- a `tool_params` section for typed, tool-specific launch settings

The model SHALL remain secret-free and SHALL NOT embed credential values, tokens, or other secret material inline.

#### Scenario: Recipe declares a launch-surface override
- **WHEN** a developer adds `launch_surface` to a brain recipe
- **THEN** the recipe remains declarative and secret-free
- **AND THEN** shared recipe loading exposes that `launch_surface` mapping to downstream build and runtime consumers

#### Scenario: Direct build uses the same launch-surface model
- **WHEN** a developer constructs a brain through direct build inputs without using a recipe
- **THEN** they can supply `BuildRequest.launch_surface_override` using the same structured model
- **AND THEN** direct-build and recipe-backed launch overrides use one shared contract

### Requirement: Launch-surface overrides merge with tool-adapter defaults under explicit precedence rules
The system SHALL treat tool-adapter launch data as the default base layer for the selected tool and SHALL merge recipe or direct-build launch-surface overrides on top of that base layer using explicit precedence rules.

For `args`, the override contract SHALL support at minimum:

- `mode = append`, which appends additional args after adapter defaults
- `mode = replace`, which replaces the adapter default arg list for recipe-owned base args

When both recipe and direct-build launch-surface overrides are present, the direct-build override SHALL take precedence over the recipe override.

#### Scenario: Recipe appends args to adapter defaults
- **WHEN** the selected tool adapter declares default launch args
- **AND WHEN** a recipe declares `launch_surface.args.mode = append`
- **THEN** the effective recipe-owned base arg list contains the adapter defaults followed by the recipe-provided args

#### Scenario: Direct build override takes precedence over recipe launch surface
- **WHEN** a recipe declares `launch_surface`
- **AND WHEN** the direct build request also declares `launch_surface_override`
- **THEN** the direct build request wins for any overlapping launch-surface fields
- **AND THEN** the effective launch-surface request is deterministic and does not depend on call-site ordering outside that precedence rule

### Requirement: Tool-specific launch params are declarative, shared-validated, and backend-scoped
The system SHALL validate `launch_surface.tool_params` through a shared typed launch-surface resolver that consumes declarative per-tool launch metadata rather than treating those settings as arbitrary untyped YAML or hardcoding optional provider launch behavior in backend classes.

That declarative launch metadata plus shared resolver SHALL define, for each supported tool param:

- the accepted key
- the accepted value type
- the backends that can honor it
- how it affects the effective launch surface

Initial v1 support SHALL include a Claude launch param named `include_partial_messages` that is valid for `claude_headless`.

#### Scenario: Supported Claude tool param validates successfully
- **WHEN** a Claude brain recipe declares `launch_surface.tool_params.include_partial_messages = true`
- **THEN** recipe validation accepts that launch param for the Claude tool family
- **AND THEN** downstream runtime resolution can consider it for `claude_headless`

#### Scenario: Optional provider behavior is not introduced only in backend code
- **WHEN** a supported tool-specific launch behavior is optional rather than protocol-required for headless operation
- **THEN** the behavior is declared through tool-adapter launch metadata and `launch_surface` support
- **AND THEN** backend `.py` code does not need to invent that optional provider flag by itself

#### Scenario: Unsupported tool param or backend combination is rejected
- **WHEN** a launch-surface request contains an unknown `tool_params` key or a known key for a backend that does not support it
- **THEN** the system fails validation or launch resolution explicitly
- **AND THEN** it does not silently keep or ignore that unsupported setting as though it were effective

### Requirement: Backend-reserved protocol args are not recipe-overridable
The system SHALL reserve backend-protocol continuity and machine-readable control args to runtime-owned backend code.

Launch-surface overrides SHALL NOT remove, replace, or contradict backend-reserved protocol args such as resume identifiers, machine-readable output-mode args, or other backend-owned control flags.

#### Scenario: Launch override conflicts with a reserved backend arg
- **WHEN** a launch-surface override attempts to inject, remove, or contradict a backend-reserved protocol arg
- **THEN** the system fails explicitly before backend start
- **AND THEN** the error identifies that the rejected setting conflicts with runtime-owned backend behavior
