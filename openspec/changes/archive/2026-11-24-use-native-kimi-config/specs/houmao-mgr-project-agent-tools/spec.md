# Spec Delta

## MODIFIED Requirements

### Requirement: Starter Kimi adapter defines managed home, launch, skills, and auth projection

The starter agent definition SHALL include a Kimi tool adapter and default setup bundle suitable for managed headless launches.

The Kimi adapter SHALL declare `tool: kimi`, `KIMI_CODE_HOME` as its home selector, `kimi` as its default executable, `skills` as its skill destination, `.` as its setup destination, and auth projections for native config and credential storage. Its env allowlist SHALL cover private input bindings supported by managed Kimi startup. The executable declaration SHALL be portable across owners.

#### Scenario: Starter Kimi adapter uses portable executable by default

- **WHEN** a project initializes or refreshes starter agent tool content
- **THEN** the Kimi adapter declares launch executable `kimi`
- **AND THEN** the starter template requires no host-specific executable path

#### Scenario: Kimi auth projection accepts OAuth token storage

- **WHEN** a selected Kimi auth bundle provides `config.toml` and `credentials/kimi-code.json`
- **THEN** the build incorporates the config into the effective runtime config and projects the token file according to the adapter mapping
- **AND THEN** the build manifest records the credential input paths without exposing token values

### Requirement: Starter Kimi environment projection matches current Kimi Code model variables

The starter Kimi adapter SHALL include `KIMI_MODEL_API_KEY` for private native config references and retain the supported sampling and global completion-cap variables as private inputs. It SHALL omit the env-model selector, config-owned provider and model fields, thinking defaults, telemetry, managed provider endpoint overrides, and obsolete thinking-mode variables.

#### Scenario: Current Kimi thinking and sampling variables survive projection

- **WHEN** the selected Kimi bundle declares a native model and an allowlisted `KIMI_MODEL_TEMPERATURE`, `KIMI_MODEL_TOP_P`, `KIMI_MODEL_MAX_TOKENS`, or `KIMI_MODEL_MAX_COMPLETION_TOKENS` value
- **THEN** the native process receives the selected value through its private launch environment
- **AND THEN** thinking defaults come from native config
- **AND THEN** the value is absent from the tmux session environment

#### Scenario: Obsolete Kimi thinking variables are not advertised

- **WHEN** a maintainer inspects the starter Kimi adapter
- **THEN** the allowlist excludes `KIMI_MODEL_NAME`, `KIMI_MODEL_THINKING_EFFORT`, `KIMI_MODEL_THINKING_KEEP`, `KIMI_DISABLE_TELEMETRY`, `KIMI_MODEL_DEFAULT_THINKING`, and `KIMI_MODEL_THINKING_MODE`
