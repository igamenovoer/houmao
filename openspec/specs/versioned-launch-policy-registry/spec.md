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

Those actions SHALL run after the selected setup baseline has been projected into the runtime home for the selected tool. They SHALL apply the resolved user-configurable values and derive the declared reserved values. Authored conflicts with reserved launch inputs SHALL fail explicitly.

Those actions SHALL support at minimum CLI argument mutation, canonicalization of equivalent launch arguments, runtime-home config or state mutation, trust or bootstrap state management, startup notice or onboarding suppression when required by the version, and pre-launch validation.

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
- **AND THEN** later actions observe the results of earlier actions for the same runtime home and working directory

#### Scenario: Codex strategy actions can canonicalize conflicting config-override args
- **WHEN** caller-supplied launch overrides set a supported native Codex approval value that differs from the unattended default
- **AND WHEN** no authored higher-priority approval field supersedes it
- **THEN** the final startup configuration applies that approval value
- **AND THEN** the strategy emits a consistent native setting

#### Scenario: Strategy-owned runtime paths are declared explicitly
- **WHEN** a developer inspects a maintained launch policy strategy
- **THEN** the strategy identifies the runtime-home files and logical keys it can write and distinguishes defaults from settings reserved for managed control
- **AND THEN** the action engine preserves unrelated provider state

### Requirement: Codex unattended strategies emit final CLI config override surfaces

For Codex unattended launch strategies, the registry-owned startup surface SHALL include final Codex CLI config override arguments for resolved strategy-managed preferences in addition to any runtime-home config mutations.

The strategy SHALL project the effective approval and sandbox settings through the highest qualified native startup precedence. It SHALL preserve recognized authored approval and sandbox values and fill omitted fields with the versioned defaults. Final arguments SHALL agree with the runtime-home projection even when project-local `.codex/config.toml` contains a different value.

#### Scenario: Codex strategy exposes CLI override ownership for startup policy
- **WHEN** a developer inspects a Codex unattended strategy entry
- **THEN** the strategy identifies the CLI config override surfaces used for the final approval and sandbox posture
- **AND THEN** runtime-home `config.toml` remains a supported projection of those resolved values

#### Scenario: Codex strategy appends final approval and sandbox overrides
- **WHEN** unattended launch resolves an authored `sandbox_mode` of `read-only` and the approval setting is omitted
- **THEN** the final Codex CLI config arguments use `read-only` and the unattended approval default
- **AND THEN** the copied runtime config and final launch arguments agree

#### Scenario: Codex strategy keeps secrets out of emitted CLI config overrides
- **WHEN** the runtime resolves a compatible Codex unattended strategy for an env-only provider launch
- **THEN** strategy-emitted CLI config overrides contain only non-secret settings
- **AND THEN** they omit API keys, auth JSON, OAuth tokens, cookies, and bearer tokens

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

### Requirement: Registry declares maintained Kimi unattended strategy coverage

The launch-policy registry SHALL include maintained Kimi Code unattended strategy coverage for `kimi_headless` and for the `raw_launch` backend used by Kimi Code local-interactive TUI launch. The compatible version expression SHALL be `>=2.1.1` with no upper version limit. Earlier versions SHALL fail compatibility validation.

Both strategies SHALL declare their minimal provider-ready inputs, evidence, startup surfaces, v2-engine requirement, native `SYSTEM.md` projection, pre-launch actions, and validation. Credential readiness SHALL remain separate from permission and role-prompt compatibility.

Kimi headless uses the native prompt entrypoint's automatic permission behavior and SHALL exclude incompatible permission flags. Kimi TUI SHALL apply the resolved permission mode at fresh or resumed provider start and use `--auto` for the unattended default. The launch SHALL establish policy through supported native startup surfaces without submitting a conversational command.

#### Scenario: Maintainer inspects Kimi native-prompt strategy metadata
- **WHEN** a maintainer inspects a Kimi headless or local-interactive strategy
- **THEN** it declares the minimum-only range, v2-engine requirement, and native `SYSTEM.md` ownership
- **AND THEN** it describes credential readiness independently

#### Scenario: Below-floor Kimi launch is rejected
- **WHEN** a managed unattended launch detects Kimi earlier than 2.1.1
- **THEN** the registry rejects the launch without selecting a fallback strategy

#### Scenario: Newer Kimi launch uses the minimum-version strategy
- **WHEN** a managed unattended launch detects a supported parseable Kimi version at or above 2.1.1
- **THEN** the registry selects the applicable minimum-version strategy for headless or TUI

#### Scenario: Headless and resumed TUI commands remain valid
- **WHEN** an unattended Kimi launch with no authored permission override selects headless or resumes a TUI
- **THEN** headless excludes incompatible permission flags
- **AND THEN** the resumed TUI uses `--auto` alongside its native continuation selector

#### Scenario: Maintainer inspects Kimi headless unattended strategy metadata
- **WHEN** a maintainer inspects the maintained Kimi headless strategy
- **THEN** the entry identifies its backend, evidence, qualified startup surfaces, and validation

#### Scenario: Maintainer inspects Kimi TUI unattended strategy metadata
- **WHEN** a maintainer inspects the maintained Kimi local-interactive strategy
- **THEN** the entry identifies `raw_launch`, the applicable native permission inputs, native `SYSTEM.md`, and v2-engine ownership
- **AND THEN** it declares policy projection at startup

#### Scenario: Kimi headless strategy rejects prompt-mode-incompatible launch args
- **WHEN** an authored permission setting requires behavior incompatible with Kimi's native prompt entrypoint
- **THEN** launch rejects that setting before invoking the provider

#### Scenario: Kimi resumed TUI keeps native auto mode
- **WHEN** an unattended Kimi TUI launch omits a permission override and resumes an existing session
- **THEN** the launch command applies native `--auto` with its continuation selector before managed input

#### Scenario: Unknown Kimi version does not silently use maintained strategy
- **WHEN** a Kimi unattended launch reports an unparseable version
- **THEN** the registry fails launch with a compatibility diagnostic

#### Scenario: Kimi TUI strategy owns automatic permission config
- **WHEN** an unattended Kimi TUI launch resolves the auto default or a supported authored permission setting
- **THEN** the selected fresh or resumed launch applies the resolved value through a qualified native startup surface
- **AND THEN** unrelated provider, model, OAuth, skill, and telemetry configuration remains intact

### Requirement: Launch-policy registry contains no Gemini strategies or hooks
The packaged launch-policy registry SHALL contain no Gemini registry file, strategy identifier, backend coverage, owned path, evidence entry, or provider hook.

#### Scenario: Registry inventory excludes Gemini
- **WHEN** a maintainer lists all packaged launch-policy strategies and hook identifiers
- **THEN** no entry names `gemini`, `gemini_cli`, or `gemini_headless`

### Requirement: Launch policy declares native system-prompt capabilities
Launch policy SHALL model native system-prompt support separately from unattended startup and provider skills. Each qualified tool/backend/version strategy used for managed role injection SHALL identify its native surface, owned path, precedence constraints, engine mode, and evidence of application before the first user turn. Skill installation or startup visibility SHALL NOT qualify as native prompt support.

#### Scenario: Kimi strategy declares native home prompt evidence
- **WHEN** a maintainer inspects a maintained Kimi 2.1.1-or-later strategy
- **THEN** the metadata identifies `<KIMI_CODE_HOME>/SYSTEM.md` as the native system-prompt surface
- **AND THEN** it identifies Kimi agent-selection precedence and v2-engine constraints that launch validation must enforce

#### Scenario: Skill support is not prompt support
- **WHEN** a provider strategy declares that skill files can be installed or are visible at startup
- **AND WHEN** it declares no native system-prompt surface
- **THEN** launch policy does not treat the skill capability as supported role injection

### Requirement: Launch policy requires native system-prompt injection
When a managed launch requires a role or system prompt, launch policy SHALL select the qualified provider strategy's native system-prompt method. It SHALL produce an explicit incompatibility result if the strategy has no applicable native method or if a higher-precedence provider input would bypass that method.

#### Scenario: Kimi selects native home system prompt
- **WHEN** a maintained Kimi 2.1.1-or-later launch requires a Houmao role or system prompt
- **THEN** launch policy selects the native managed-home `SYSTEM.md` method
- **AND THEN** it selects neither managed auto-skill injection nor ordinary chat bootstrap

#### Scenario: Unsupported provider reports incompatibility
- **WHEN** a managed launch requires a role or system prompt
- **AND WHEN** the qualified strategy has no applicable native system-prompt method
- **THEN** strategy resolution reports that no supported injection method exists for that tool, backend, and version

### Requirement: Unattended supplies versioned native permission defaults

Each maintained unattended strategy SHALL declare the most permissive supported permission and approval defaults for its tool version and backend. It SHALL apply each default only to an omitted field. Effective launch diagnostics SHALL identify resolved permission values and their source without exposing credentials.

#### Scenario: No permission settings are supplied

- **WHEN** a managed unattended launch supplies no permission settings
- **THEN** the selected strategy applies the most permissive qualified native posture without routine operator approvals
- **AND THEN** enforced provider policy and the selected execution identity bound the available authority

#### Scenario: Authored permission mode is intentionally interactive

- **WHEN** a user requests unattended defaults and explicitly configures a supported mode that asks for approval
- **THEN** the native launch uses that mode
- **AND THEN** diagnostics attribute the effective mode to the user's setting

#### Scenario: The backend cannot apply a permission value

- **WHEN** the detected tool or selected backend cannot honor an effective authored permission value
- **THEN** launch validation identifies the setting, version, and backend before provider start or managed takeover

#### Scenario: As-is uses the selected native baseline

- **WHEN** a launch requests `as_is` and omits a permission setting
- **THEN** the launch uses the native baseline for that setting
- **AND THEN** a prior Houmao-generated unattended value does not count as an authored override
