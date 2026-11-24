# Spec Delta

## ADDED Requirements

### Requirement: Kimi preflight and startup share effective native config

Houmao SHALL resolve effective Kimi TOML before home creation or managed replacement. It SHALL use that config for model and reasoning validation and materialize it in the private `KIMI_CODE_HOME` before applying runtime-owned settings. Credential config SHALL overlay setup settings, including complete replacement of matching provider, model, and service entries. Distinct entries and setup-only settings SHALL survive.

#### Scenario: Preflight finds an alias in the credential config

- **WHEN** a Kimi profile selects an alias and numeric reasoning level from a catalog declared only in the credential bundle's `config.toml`
- **THEN** preflight validates the alias and level using that catalog
- **AND THEN** the runtime config contains that alias and the selected native effort

#### Scenario: The credential config replaces only its declared entries

- **WHEN** a secret-free Kimi setup config sets telemetry, supplies a model alias, and defines a provider
- **AND WHEN** the credential config supplies another alias and a replacement for that provider with a different endpoint
- **THEN** the runtime config contains both aliases and the setup telemetry setting
- **AND THEN** the replacement provider contains the credential config's entry without carrying setup auth or headers across the endpoint change

#### Scenario: Invalid inputs fail before replacing a predecessor

- **WHEN** a forced Kimi launch selects invalid TOML or requests a level for an alias with a malformed catalog
- **THEN** preflight fails with a diagnostic identifying the file or alias and field
- **AND THEN** the predecessor remains running and the candidate config has not been materialized

### Requirement: Kimi runtime homes deliver native config and private credentials

Managed Kimi startup SHALL use a private home selected by `KIMI_CODE_HOME`. The home SHALL support both config-backed API providers and imported OAuth token storage. The runtime SHALL deliver a TOML-referenced environment credential from the selected credential inputs to the provider only and exclude credential values from tmux and public diagnostics.

#### Scenario: Config-backed API provider uses a private key reference

- **WHEN** a Kimi provider declares `api_key_env = "KIMI_MODEL_API_KEY"` and the selected bundle contains that key
- **THEN** the provider uses its configured model and endpoint with the selected key
- **AND THEN** the key is absent from the tmux session environment, ordinary panes, pane command, and public outputs

#### Scenario: The managed home supports imported OAuth and inline API keys

- **WHEN** the selected Kimi config references imported OAuth storage or supplies an inline key from a private credential bundle
- **THEN** Kimi receives the effective config in its private home and the matching token file for OAuth
- **AND THEN** provider startup does not depend on the operator's user-global Kimi home

### Requirement: Kimi launch excludes environment bindings owned by native config

Every managed Kimi provider start SHALL use native TOML for settings with supported persistent equivalents. Houmao SHALL reject explicitly authored config-owned env values with a TOML diagnostic, omit ambient values for those names, and mask stale or inherited bindings in the owning tmux session. Env-only process controls and private credential bindings SHALL remain available through their supported channels.

#### Scenario: Legacy environment-only Kimi launch requires native config

- **WHEN** a selected Kimi auth bundle or saved launch record uses `KIMI_MODEL_NAME` or another retired model/provider binding
- **THEN** launch fails before provider startup with the setting name and replacement TOML location
- **AND THEN** the diagnostic omits the rejected value

#### Scenario: Explicit runtime preference overrides use native config

- **WHEN** a Kimi specialist record or `--env-set` supplies `KIMI_DISABLE_TELEMETRY` or a loop limit with a persistent TOML equivalent
- **THEN** Houmao identifies the native setting to edit and rejects the env assignment without starting the agent

#### Scenario: Fresh launch and relaunch mask inherited Kimi configuration variables

- **WHEN** a Kimi launch or relaunch uses native config and its tmux server or invoking process has a stale `KIMI_MODEL_NAME`, `KIMI_MODEL_THINKING_EFFORT`, or other config-owned value
- **THEN** the native process and new panes in its owned session have no binding for those names
- **AND THEN** native config selects the model and reasoning effort
- **AND THEN** Houmao does not modify the server-global values or peer sessions

## REMOVED Requirements

### Requirement: Kimi managed runtime homes support OAuth and env-model credentials

**Reason**: The env-model path creates a separate runtime model catalog that bypasses native model and effort definitions.

**Migration**: Define the provider and model in Kimi `config.toml` and remove retired environment bindings. Use private Kimi API-key inputs or import the native OAuth config and matching tokens.
