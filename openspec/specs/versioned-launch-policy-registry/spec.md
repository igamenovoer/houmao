## Purpose
Define the runtime-owned registry contract for version-scoped launch-policy strategies that suppress startup operator prompts for supported tools and backends.

## Requirements

### Requirement: Launch policy strategies are version-scoped and runtime-owned
The system SHALL maintain a runtime-owned launch policy registry for supported tools and backends. Each registry strategy SHALL bind one operator prompt policy mode to one or more compatible tool-version ranges and backends.

The registry SHALL be stored as repo-owned YAML under `src/houmao/agents/launch_policy/registry/`.

Each registry document SHALL expose a concrete schema that can represent:

- top-level `schema_version`
- top-level `tool`
- one or more strategy entries with `strategy_id`, `operator_prompt_mode`, `backends`, and `supported_versions`
- strategy `minimal_inputs`
- strategy `evidence`
- strategy `owned_paths`
- strategy `actions`

The `supported_versions` field SHALL use one dependency-style version-specifier expression per strategy entry (for example `>=2.1.81,<2.2`) and strategy resolution SHALL continue to fail explicitly when the detected tool version matches no declared supported range.

#### Scenario: Same tool selects different strategies for different versions
- **WHEN** two installed versions of the same CLI tool request the same operator prompt policy
- **AND WHEN** those versions match different compatible declared supported-version ranges
- **THEN** the registry MAY select different launch policy strategies for those versions
- **AND THEN** strategy selection remains deterministic for a given tool, backend, policy mode, and detected version

### Requirement: Strategies declare minimal input contract and evidence provenance
Each launch policy strategy SHALL declare the minimal input contract it supports and the evidence basis for its behavior assumptions.

At minimum, strategy metadata SHALL be able to describe:

- the supported credential/input forms
- whether user-prepared provider config/state files are required
- which parts of the strategy are backed by official docs, local source/reference analysis, or live-probe observations
- which runtime-owned file paths and logical subpaths the strategy is allowed to mutate

#### Scenario: Strategy metadata distinguishes documented behavior from observed state
- **WHEN** a developer inspects a registry strategy for a supported tool version
- **THEN** they can identify whether the strategy is intended to work from minimal credentials alone
- **AND THEN** they can identify which startup-suppression assumptions came from official docs versus source/live validation
- **AND THEN** they can identify the runtime-owned files and subpaths that strategy claims as mutable surface

### Requirement: Launch policy strategies define ordered pre-launch actions
A launch policy strategy SHALL define the ordered actions that must be applied before provider start to satisfy the requested prompt policy for the resolved working directory and runtime home.

Those actions SHALL support at minimum CLI argument mutation, runtime-home config or state mutation, trust or bootstrap state management, startup notice/onboarding suppression when required by the version, and pre-launch validation.

The canonical generic action vocabulary SHALL include at minimum:

- `cli_arg.ensure_present`
- `cli_arg.ensure_absent`
- `json.set`
- `toml.set`
- `validate.reject_conflicting_launch_args`
- `provider_hook.call`

Provider-specific complex behavior SHALL be exposed through stable hook ids referenced from `provider_hook.call`, not through arbitrary executable code embedded in the registry file.

#### Scenario: Strategy applies ordered actions before provider start
- **WHEN** the runtime resolves a compatible launch policy strategy
- **THEN** it applies the strategy's ordered actions before provider process start
- **AND THEN** later actions observe the results of earlier strategy actions for the same runtime home and working directory

#### Scenario: Codex strategy actions include trust and migration-state handling when required by the version
- **WHEN** the runtime resolves a Codex unattended strategy for a version whose fresh-home startup stops on trust and then a model migration notice
- **THEN** the ordered action set may include trust state mutation plus model/notice state mutation before provider start
- **AND THEN** unattended compatibility is evaluated against the full observed startup sequence for that version

#### Scenario: Strategy-owned runtime paths are declared explicitly
- **WHEN** a developer inspects a Claude or Codex unattended strategy entry
- **THEN** the entry declares the runtime-owned files and logical keys it may mutate, such as specific JSON paths in `.claude.json` or TOML keys in `config.toml`
- **AND THEN** the action engine does not treat unrelated provider state as strategy-owned by implication

### Requirement: Unattended strategy compatibility failures are explicit
For operator prompt policies that forbid startup operator prompts, the registry SHALL treat unknown or incompatible tool versions as explicit launch failures by default rather than silently falling back to a best-effort strategy.

#### Scenario: Unknown newer version does not use silent floor fallback
- **WHEN** a prompt-forbidden launch requests a tool version newer than any compatible registry strategy
- **THEN** the registry reports that no compatible strategy exists
- **AND THEN** launch fails explicitly instead of using a silent compatibility fallback

### Requirement: Controlled unattended-strategy overrides stay transient
The registry resolution path SHALL allow a transient strategy-id override for controlled experiments without turning that override into persisted build-time policy.

#### Scenario: Override strategy id is not persisted into build artifacts
- **WHEN** `HOUMAO_LAUNCH_POLICY_OVERRIDE_STRATEGY` selects a registry strategy for an unattended launch
- **THEN** resolution may use that strategy id for the current process
- **AND THEN** the override does not alter the registry YAML, the recipe, or the resolved brain manifest
