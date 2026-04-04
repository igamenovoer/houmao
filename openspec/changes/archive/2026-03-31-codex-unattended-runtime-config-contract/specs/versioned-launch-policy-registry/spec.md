## MODIFIED Requirements

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
