## MODIFIED Requirements

### Requirement: Runtime unattended launch can synthesize provider startup state from minimal credentials
When unattended launch is requested, the runtime SHALL construct provider startup state by starting from the selected setup-projected runtime home and then allowing the selected strategy to create, patch, or validate strategy-owned provider config/state and launch surfaces before process start.

Unattended compatibility SHALL be evaluated independently from credential readiness. The runtime SHALL NOT define unattended support in terms of `auth.json`, API-key presence, or other secret material alone.

For strategy-owned unattended surfaces, the runtime SHALL NOT depend on pre-existing values in copied setup files or on caller-supplied launch args to reach unattended startup.

The runtime SHALL NOT require pre-existing user-owned tool config files solely to suppress startup prompts.

This contract SHALL apply to any Houmao-launched agent backend that supports unattended launch, whether the provider surface is TUI or headless.

#### Scenario: Fresh runtime home launches unattended from setup baseline plus strategy-owned overrides
- **WHEN** a session starts from a brain manifest that requests `operator_prompt_mode = unattended`
- **AND WHEN** the selected tool setup projects a baseline `config.toml` into a fresh runtime home
- **THEN** the runtime copies that setup baseline first
- **AND THEN** the selected strategy may patch its declared runtime-owned config keys and launch surfaces before provider start
- **AND THEN** unattended launch does not depend on a pre-existing user-authored no-prompt home directory

#### Scenario: Missing credential fails readiness without redefining unattended compatibility
- **WHEN** a session requests `operator_prompt_mode = unattended`
- **AND WHEN** a compatible unattended strategy exists for the detected tool version and backend
- **AND WHEN** the resolved provider still lacks the required secret material after provider selection is known
- **THEN** the runtime fails before provider start with a credential-readiness error
- **AND THEN** the failure does not report that unattended compatibility itself was unsupported

#### Scenario: Claude unattended launch follows the same authoritative contract
- **WHEN** a Claude Code session requests `operator_prompt_mode = unattended`
- **THEN** the runtime treats Claude's declared no-prompt state and launch surfaces as Houmao-owned for provider start
- **AND THEN** unattended startup does not depend on pre-existing Claude config files or caller-supplied low-level startup flags

### Requirement: Strategy-owned launch args are not silently overridden
When unattended launch is requested, the selected strategy SHALL own the effective no-prompt CLI args it requires and the equivalent caller launch-override surfaces that map onto strategy-owned runtime config.

The runtime SHALL canonicalize the effective launch request before provider start so strategy-owned unattended behavior wins over contradictory caller launch inputs.

For tools such as Codex that support config-override args, the runtime SHALL also canonicalize caller overrides that target strategy-owned unattended config keys even when the conflict is expressed through generic config-override syntax rather than a dedicated flag.

#### Scenario: Conflicting launch override is canonicalized to the unattended strategy
- **WHEN** a session requests `operator_prompt_mode = unattended`
- **AND WHEN** caller-supplied `launch_args_override` conflicts with a strategy-owned no-prompt arg or removes required strategy behavior
- **THEN** the runtime canonicalizes the effective launch args before provider start so the strategy-owned unattended behavior still applies
- **AND THEN** the final effective launch behavior does not depend on the caller-supplied conflicting arg

#### Scenario: Conflicting Codex config-override arg is canonicalized to the unattended strategy
- **WHEN** a session requests `operator_prompt_mode = unattended`
- **AND WHEN** caller-supplied launch overrides include a Codex `-c` config override for a strategy-owned unattended key such as `approval_policy`, `sandbox_mode`, or project trust
- **THEN** the runtime canonicalizes the effective startup surface before provider start so the strategy-owned unattended value still applies
- **AND THEN** the launch does not depend on the caller-supplied conflicting config value to become unattended

## ADDED Requirements

### Requirement: Unattended runtime-owned config overrides replace conflicting setup values in the runtime home
When unattended launch is requested, the runtime SHALL treat strategy-owned runtime-home config keys as authoritative for provider start even when the copied setup baseline defines different values for those same keys.

The runtime SHALL preserve non-owned setup content in the runtime home, including provider-selection and model-provider configuration, unless a declared strategy-owned mutation explicitly changes that content.

#### Scenario: Codex unattended launch overwrites copied setup approval settings
- **WHEN** a selected Codex setup baseline defines `approval_policy` or `sandbox_mode` values in `config.toml`
- **AND WHEN** the brain manifest requests `operator_prompt_mode = unattended`
- **THEN** the runtime overwrites those strategy-owned keys in the runtime-home `config.toml` before provider start
- **AND THEN** unrelated setup-defined provider configuration remains intact

#### Scenario: Claude unattended launch preserves non-owned baseline content while overriding owned startup state
- **WHEN** a selected Claude setup baseline includes provider-specific defaults that are not strategy-owned unattended state
- **AND WHEN** the brain manifest requests `operator_prompt_mode = unattended`
- **THEN** the runtime preserves that non-owned baseline content
- **AND THEN** it still overwrites Claude's declared unattended-owned startup state before provider start

### Requirement: Unattended runtime-owned launch surfaces replace conflicting caller launch inputs
When unattended launch is requested, the runtime SHALL treat strategy-owned launch args and equivalent config-override surfaces as authoritative for provider start even when the caller requested different values.

The runtime MAY preserve caller-supplied diagnostics or provenance, but the final effective startup behavior SHALL be determined by the unattended strategy rather than by the caller's conflicting low-level launch inputs.

This rule SHALL apply equally to current tools such as Claude Code and Codex and to future Houmao-launched tools that declare unattended-owned launch surfaces.

#### Scenario: Codex unattended launch replaces caller startup-policy flags
- **WHEN** a caller requests unattended launch for Codex
- **AND WHEN** the caller also supplies direct launch flags or `-c` config overrides that would weaken unattended startup behavior
- **THEN** the runtime replaces or removes those conflicting effective startup inputs before provider start
- **AND THEN** the resulting Codex launch still uses the unattended strategy's startup policy

#### Scenario: Claude unattended launch replaces caller startup-policy flags
- **WHEN** a caller requests unattended launch for Claude Code
- **AND WHEN** the caller also supplies low-level startup inputs that would weaken the unattended strategy's owned launch surfaces
- **THEN** the runtime replaces or removes those conflicting effective startup inputs before provider start
- **AND THEN** the resulting Claude launch still uses the unattended strategy's startup policy
