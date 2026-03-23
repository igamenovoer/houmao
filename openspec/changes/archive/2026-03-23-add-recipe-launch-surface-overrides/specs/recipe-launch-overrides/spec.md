## ADDED Requirements

### Requirement: Structured launch overrides are available to recipes and direct builds
The system SHALL support an optional structured `launch_overrides` model for per-brain tool-launch behavior.

That model SHALL be available through:

- declarative recipe YAML at `launch_overrides`
- direct build inputs at `BuildRequest.launch_overrides`

The model SHALL support at minimum:

- an `args` section for raw CLI argument override behavior
- a `tool_params` section for typed, tool-specific launch settings

The model SHALL remain secret-free and SHALL NOT embed credential values, tokens, or other secret material inline.

#### Scenario: Recipe declares launch overrides
- **WHEN** a developer adds `launch_overrides` to a brain recipe
- **THEN** the recipe remains declarative and secret-free
- **AND THEN** shared recipe loading exposes that `launch_overrides` mapping to downstream build and runtime consumers

#### Scenario: Direct build uses the same launch-overrides model
- **WHEN** a developer constructs a brain through direct build inputs without using a recipe
- **THEN** they can supply `BuildRequest.launch_overrides` using the same structured model
- **AND THEN** direct-build and recipe-backed launch overrides use one shared contract

### Requirement: Launch overrides merge with tool-adapter defaults under explicit section precedence rules
The system SHALL treat tool-adapter launch data as the default base layer for the selected tool and SHALL merge recipe or direct-build launch overrides on top of that base layer using explicit precedence rules.

For `args`, the override contract SHALL support at minimum:

- `mode = append`, which appends additional args after adapter defaults
- `mode = replace`, which replaces the adapter default arg list for the winning override section

When both recipe and direct-build launch overrides are present:

- unmentioned top-level sections SHALL survive from lower-priority layers
- `tool_params` SHALL merge per key
- `args` SHALL be an atomic section
- if a higher-priority layer provides `args`, that `args` section replaces lower-priority `args`
- `args.mode` SHALL evaluate against adapter defaults after section precedence is decided

#### Scenario: Recipe appends args to adapter defaults
- **WHEN** the selected tool adapter declares default launch args
- **AND WHEN** a recipe declares `launch_overrides.args.mode = append`
- **THEN** the effective recipe-owned base arg list contains the adapter defaults followed by the recipe-provided args

#### Scenario: Direct build args override does not drop recipe tool params
- **WHEN** a recipe declares `launch_overrides.tool_params.include_partial_messages = true`
- **AND WHEN** the direct build request declares only `launch_overrides.args`
- **THEN** the direct build request wins for the `args` section
- **AND THEN** the recipe-owned `tool_params.include_partial_messages` value survives unchanged

#### Scenario: Direct build args section replaces recipe args section
- **WHEN** a recipe declares `launch_overrides.args`
- **AND WHEN** the direct build request also declares `launch_overrides.args`
- **THEN** the direct build `args` section replaces the recipe `args` section
- **AND THEN** the winning `args.mode` evaluates against adapter defaults rather than composing modes across layers

### Requirement: Tool-specific launch params are declarative, shared-validated, and backend-scoped
The system SHALL validate `launch_overrides.tool_params` through a shared typed launch-overrides resolver that consumes declarative per-tool launch metadata rather than treating those settings as arbitrary untyped YAML or hardcoding optional provider launch behavior in backend classes.

That declarative launch metadata plus shared resolver SHALL define, for each supported tool param:

- the accepted key
- the accepted value type
- the backends that can honor it
- how it affects the effective launch behavior

Initial v1 support SHALL include a Claude launch param named `include_partial_messages` that is valid for `claude_headless`.

Gemini SHALL start with an empty supported typed-tool-param set in v1.

#### Scenario: Supported Claude tool param validates successfully
- **WHEN** a Claude brain recipe declares `launch_overrides.tool_params.include_partial_messages = true`
- **THEN** recipe validation accepts that launch param for the Claude tool family
- **AND THEN** downstream runtime resolution can consider it for `claude_headless`

#### Scenario: Gemini typed tool params are rejected in v1
- **WHEN** a Gemini brain recipe declares any `launch_overrides.tool_params` key
- **THEN** the system fails validation or launch resolution explicitly
- **AND THEN** the error identifies that Gemini exposes no supported typed tool params in v1

#### Scenario: Optional provider behavior is not introduced only in backend code
- **WHEN** a supported tool-specific launch behavior is optional rather than protocol-required for headless operation
- **THEN** the behavior is declared through tool-adapter launch metadata and `launch_overrides` support
- **AND THEN** backend `.py` code does not need to invent that optional provider flag by itself

#### Scenario: Unsupported tool param or backend combination is rejected
- **WHEN** a launch-overrides request contains an unknown `tool_params` key or a known key for a backend that does not support it
- **THEN** the system fails validation or launch resolution explicitly
- **AND THEN** it does not silently keep or ignore that unsupported setting as though it were effective

### Requirement: Backend-reserved protocol args are not recipe-overridable
The system SHALL reserve backend-protocol continuity and machine-readable control args to runtime-owned backend code.

Launch overrides SHALL NOT remove, replace, or contradict backend-reserved protocol args such as resume identifiers, machine-readable output-mode args, or other backend-owned control flags.

#### Scenario: Launch override conflicts with a reserved backend arg
- **WHEN** a launch-overrides request attempts to inject, remove, or contradict a backend-reserved protocol arg
- **THEN** the system fails explicitly before backend start
- **AND THEN** the error identifies that the rejected setting conflicts with runtime-owned backend behavior
