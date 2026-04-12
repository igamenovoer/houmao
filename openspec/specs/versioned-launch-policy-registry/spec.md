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
Each launch policy strategy SHALL declare the unattended-compatibility contract it supports and the evidence basis for its behavior assumptions.

This unattended-compatibility ownership model SHALL apply to every Houmao-launched agent backend that participates in the launch-policy registry, whether TUI or headless.

At minimum, strategy metadata SHALL be able to describe:

- the startup-suppression surfaces the strategy owns, including runtime-home file paths, logical subpaths, and equivalent launch-arg surfaces,
- the credential-readiness inputs or validation contract required after provider selection is resolved,
- whether user-prepared provider config/state files are required,
- which parts of the strategy are backed by official docs, local source/reference analysis, or live-probe observations,
- which runtime-owned file paths and logical subpaths the strategy is allowed to mutate.

Credential-readiness metadata SHALL remain separate from unattended-compatibility metadata. A strategy SHALL NOT imply that `auth.json`, API-key presence, or other secret material is itself the definition of no-prompt startup compatibility.

#### Scenario: Strategy metadata separates unattended compatibility from credential readiness
- **WHEN** a developer inspects a registry strategy for a supported tool version
- **THEN** they can identify which startup prompts the strategy suppresses through runtime-owned config or launch surfaces
- **AND THEN** they can identify the credential-readiness contract separately from that no-prompt startup contract
- **AND THEN** the strategy metadata does not treat a secret form by itself as proof that unattended startup is supported

#### Scenario: Strategy metadata identifies runtime-owned config surfaces explicitly
- **WHEN** a developer inspects a Codex unattended strategy entry
- **THEN** the entry declares the runtime-owned `config.toml` keys and equivalent launch-override surfaces it owns
- **AND THEN** provider-defining setup content outside those declared owned surfaces remains part of the copied baseline rather than implicit strategy ownership

#### Scenario: Future tool strategy uses the same unattended ownership model
- **WHEN** a future Houmao-launched tool adds an unattended strategy to the registry
- **THEN** that strategy declares the runtime-owned startup surfaces Houmao must control for unattended launch
- **AND THEN** the same separation between setup baseline, unattended ownership, and credential readiness applies to that new tool

### Requirement: Launch policy strategies define ordered pre-launch actions
A launch policy strategy SHALL define the ordered actions that must be applied before provider start to satisfy the requested prompt policy for the resolved working directory and runtime home.

Those actions SHALL run after the selected setup baseline has been projected into the runtime home for the selected tool.

Those actions SHALL support at minimum CLI argument mutation, canonicalization of caller launch args including config-override args that target strategy-owned runtime config, runtime-home config or state mutation, trust or bootstrap state management, startup notice/onboarding suppression when required by the version, and pre-launch validation.

For supported TUI and headless backends, the registry SHALL treat those runtime-owned startup surfaces as authoritative whenever `operator_prompt_mode = unattended`.

The canonical generic action vocabulary SHALL include at minimum:

- `cli_arg.ensure_present`
- `cli_arg.ensure_absent`
- `json.set`
- `toml.set`
- `validate.reject_conflicting_launch_args`
- `provider_hook.call`

Provider-specific complex behavior SHALL be exposed through stable hook ids referenced from `provider_hook.call`, not through arbitrary executable code embedded in the registry file.

#### Scenario: Strategy applies ordered actions after setup baseline projection
- **WHEN** the runtime resolves a compatible launch policy strategy
- **AND WHEN** the selected tool setup has already been copied into the runtime home
- **THEN** the runtime applies the strategy's ordered actions against that runtime copy before provider process start
- **AND THEN** later actions observe the results of earlier strategy actions for the same runtime home and working directory

#### Scenario: Codex strategy actions can canonicalize conflicting config-override args
- **WHEN** the runtime resolves a Codex unattended strategy
- **AND WHEN** caller-supplied launch overrides include a `-c` config override or direct flag that targets a strategy-owned no-prompt surface such as `approval_policy` or `sandbox_mode`
- **THEN** ordered pre-launch actions canonicalize the effective startup surface so the strategy-owned unattended behavior still applies before provider start
- **AND THEN** the runtime does not depend on the caller-supplied conflicting value to achieve unattended startup

#### Scenario: Strategy-owned runtime paths are declared explicitly
- **WHEN** a developer inspects a Claude or Codex unattended strategy entry
- **THEN** the entry declares the runtime-owned files and logical keys it may mutate, such as specific JSON paths in `.claude.json` or TOML keys in `config.toml`
- **AND THEN** the action engine does not treat unrelated provider state as strategy-owned by implication

### Requirement: Codex unattended strategies emit final CLI config override surfaces
For Codex unattended launch strategies, the registry-owned startup surface SHALL include final Codex CLI config override arguments for strategy-owned non-secret preferences in addition to any runtime-home config mutations.

The strategy action path SHALL canonicalize conflicting caller launch inputs before emitting those final CLI config overrides, so the final provider start uses the strategy-owned unattended posture even when copied setup config, caller launch overrides, or cwd/project `.codex/config.toml` define conflicting values.

At minimum, Codex unattended strategy final CLI config override emission SHALL cover strategy-owned approval and sandbox posture. It MAY also cover other non-secret strategy-owned Codex startup preferences when the strategy declares ownership for those keys.

#### Scenario: Codex strategy exposes CLI override ownership for startup policy
- **WHEN** a developer inspects a Codex unattended strategy entry
- **THEN** the strategy identifies the CLI config override surfaces it owns for unattended startup policy
- **AND THEN** runtime-home `config.toml` mutation remains documented as fallback and repair state rather than the only authority boundary

#### Scenario: Codex strategy appends final approval and sandbox overrides
- **WHEN** the runtime resolves a compatible Codex unattended strategy
- **AND WHEN** caller launch args include a conflicting Codex `-c approval_policy="on-request"` or `-c sandbox_mode="read-only"` override
- **THEN** the strategy canonicalizes the conflicting caller inputs
- **AND THEN** the final Codex process arguments include strategy-owned CLI config overrides for unattended approval and sandbox posture
- **AND THEN** cwd/project Codex config layers cannot weaken the maintained unattended startup posture

#### Scenario: Codex strategy keeps secrets out of emitted CLI config overrides
- **WHEN** the runtime resolves a Codex unattended strategy for an env-only provider launch
- **THEN** the strategy may emit non-secret CLI config override args needed for startup-policy or provider-selection correctness
- **AND THEN** the strategy does not emit API key values, auth JSON, OAuth tokens, cookies, or bearer tokens in CLI args

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

### Requirement: Registry declares maintained Gemini unattended headless strategy coverage
The launch-policy registry SHALL include maintained Gemini unattended strategy coverage for the `gemini_headless` backend.

That Gemini strategy coverage SHALL remain version-scoped and SHALL declare:

- the compatible Gemini CLI version range,
- the minimal input contract needed after provider selection is resolved,
- evidence provenance for the maintained no-prompt behavior assumptions,
- any runtime-owned Gemini startup surfaces or provider hooks Houmao must control,
- the ordered actions needed before Gemini provider start.

The Gemini strategy metadata SHALL separate credential readiness from unattended startup compatibility and SHALL describe Gemini's maintained auth readiness in terms of the already-supported Gemini auth families rather than inventing a separate unattended-only auth contract.

#### Scenario: Maintainer inspects Gemini unattended strategy metadata
- **WHEN** a maintainer inspects the launch-policy registry entry that covers maintained Gemini unattended startup
- **THEN** the entry declares `gemini_headless` as a supported backend
- **AND THEN** it declares the compatible Gemini version range, evidence basis, owned startup surfaces or hooks, and ordered actions
- **AND THEN** it keeps credential readiness distinct from the unattended startup ownership model
