## MODIFIED Requirements

### Requirement: Gemini headless runtime honors unattended launch policy when compatible registry coverage exists
When a session requests `operator_prompt_mode = unattended` on the `gemini_headless` backend and a compatible Gemini launch-policy strategy exists for the detected Gemini CLI version, the runtime SHALL apply that strategy before provider process start and SHALL allow Gemini startup to continue on the maintained unattended path with full built-in tool availability and no interactive approval prompts.

The maintained Gemini unattended strategy SHALL own the effective approval posture and sandbox posture for runtime-owned Gemini headless launches.

#### Scenario: Compatible Gemini unattended strategy enables headless provider start with full-permission posture
- **WHEN** a session requests `operator_prompt_mode = unattended`
- **AND WHEN** the selected backend is `gemini_headless`
- **AND WHEN** the detected Gemini CLI version matches one compatible maintained Gemini strategy
- **THEN** the runtime applies the Gemini unattended strategy before provider start
- **AND THEN** the effective Gemini startup uses the strategy-owned approval and sandbox posture rather than the headless default read-only posture
- **AND THEN** Gemini startup continues on the unattended headless path without interactive approval prompts

#### Scenario: Managed Gemini unattended turn preserves shell and write tool availability
- **WHEN** the runtime starts or resumes a runtime-owned Gemini headless session under unattended launch policy
- **THEN** the effective Gemini turn keeps built-in shell and file mutation tools available to the managed prompt
- **AND THEN** the runtime does not leave those tools absent from the active tool registry only because the backend is non-interactive

### Requirement: Unattended runtime-owned config overrides replace conflicting setup values in the runtime home
When unattended launch is requested, the runtime SHALL treat strategy-owned runtime-home config keys as authoritative for provider start even when the copied setup baseline defines different values for those same keys.

The runtime SHALL preserve non-owned setup content in the runtime home, including provider-selection and model-provider configuration, unless a declared strategy-owned mutation explicitly changes that content.

This rule SHALL apply to any provider that declares strategy-owned runtime-home config state for unattended launch, including Gemini when copied runtime-home settings would otherwise weaken the maintained unattended approval, sandbox, or tool-availability posture.

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

#### Scenario: Gemini unattended launch overwrites copied startup-policy settings
- **WHEN** a selected Gemini setup baseline or runtime-home settings file defines approval, sandbox, or tool-availability keys that would weaken the maintained unattended posture
- **AND WHEN** the brain manifest requests `operator_prompt_mode = unattended`
- **THEN** the runtime overwrites or removes those strategy-owned Gemini keys before provider start
- **AND THEN** unrelated setup-defined Gemini configuration remains intact

### Requirement: Unattended runtime-owned launch surfaces replace conflicting caller launch inputs
When unattended launch is requested, the runtime SHALL treat strategy-owned launch args and equivalent config-override surfaces as authoritative for provider start even when the caller requested different values.

The runtime MAY preserve caller-supplied diagnostics or provenance, but the final effective startup behavior SHALL be determined by the unattended strategy rather than by the caller's conflicting low-level launch inputs.

This rule SHALL apply equally to current tools such as Claude Code, Codex, and Gemini and to future Houmao-launched tools that declare unattended-owned launch surfaces.

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

#### Scenario: Gemini unattended launch replaces caller startup-policy flags
- **WHEN** a caller requests unattended launch for Gemini
- **AND WHEN** the caller also supplies low-level Gemini launch flags that would weaken the unattended strategy's owned approval, sandbox, or tool-availability posture
- **THEN** the runtime replaces or removes those conflicting effective startup inputs before provider start
- **AND THEN** the resulting Gemini launch still uses the maintained unattended full-permission posture
