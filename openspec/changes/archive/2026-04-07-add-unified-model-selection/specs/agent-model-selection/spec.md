## ADDED Requirements

### Requirement: Unified model configuration is launch-owned and secret-free
The system SHALL expose a tool-agnostic model-configuration field as launch configuration rather than as auth-owned or setup-owned user-facing state.

Recipes or specialists MAY persist a default model name.

Recipes, specialists, or launch profiles MAY also persist an optional normalized reasoning level as part of that same launch-owned model configuration.

Launch profiles MAY persist reusable model and reasoning overrides.

Direct launch surfaces MAY provide one-off model and reasoning overrides.

The normalized reasoning field SHALL be an integer in the inclusive range `1..10`.

This field SHALL remain secret-free and SHALL NOT require operators to author tool-specific env vars, auth-bundle values, or setup-file edits directly.

Persistent env authoring surfaces SHALL NOT become the supported way to specify the model-configuration field.

#### Scenario: Source and profile defaults are treated as launch configuration
- **WHEN** a recipe stores default model `gpt-5.4` with reasoning level `6`
- **AND WHEN** a launch profile stores default model `gpt-5.4-mini` with reasoning level `4`
- **THEN** Houmao persists those values as launch-owned configuration
- **AND THEN** neither value is treated as inline credential material

#### Scenario: Stored normalized reasoning level must remain in range
- **WHEN** an operator attempts to author reasoning level `0` or `11`
- **THEN** the system rejects the value clearly
- **AND THEN** the accepted normalized range remains exactly `1..10`

### Requirement: Effective model configuration follows explicit precedence
The system SHALL resolve the effective model configuration using this precedence order:

1. copied tool-native baseline or legacy setup/auth fallback
2. source recipe or specialist launch default
3. launch-profile default
4. direct CLI launch override
5. runtime-only in-session mutation

Fields omitted by a higher-priority layer SHALL survive from the next lower-priority layer.

Runtime-only in-session mutation SHALL remain non-persistent and SHALL NOT rewrite recipe, specialist, or launch-profile state.

#### Scenario: Launch-profile model overrides the source default
- **WHEN** a source recipe stores default model `gpt-5.4`
- **AND WHEN** the selected launch profile stores default model `gpt-5.4-mini`
- **AND WHEN** the operator supplies no direct model override
- **THEN** the effective launched model is `gpt-5.4-mini`

#### Scenario: Reasoning level resolves independently from model name
- **WHEN** a source recipe stores model `gpt-5.4` with reasoning level `7`
- **AND WHEN** the selected launch profile stores only reasoning level `3`
- **AND WHEN** the operator supplies no direct model override
- **THEN** the effective launched model remains `gpt-5.4`
- **AND THEN** the effective launched reasoning level is `3`

#### Scenario: Direct launch override wins over the profile defaults
- **WHEN** a source recipe stores model `gpt-5.4` with reasoning level `6`
- **AND WHEN** the selected launch profile stores model `gpt-5.4-mini` with reasoning level `4`
- **AND WHEN** the operator launches with direct overrides `--model gpt-5.4-nano --reasoning-level 9`
- **THEN** the effective launched model is `gpt-5.4-nano`
- **AND THEN** the effective launched reasoning level is `9`
- **AND THEN** the stored recipe and launch-profile defaults remain unchanged

#### Scenario: Legacy copied native state survives when no unified value is supplied
- **WHEN** copied setup or auth state already selects one tool-native model or reasoning setting
- **AND WHEN** no recipe, specialist, launch profile, or direct launch input supplies a unified launch-owned model value for that subfield
- **THEN** the launched runtime continues using that copied tool-native state
- **AND THEN** Houmao does not require the operator to backfill a unified model field before launch succeeds

### Requirement: Resolved model configuration is projected into tool-native runtime state
Before provider startup, the system SHALL project the resolved model configuration into the constructed runtime home or launch environment using supported tool-native startup surfaces.

At minimum, the maintained direct model-name projection targets SHALL be:

- Claude: launch environment variable `ANTHROPIC_MODEL`
- Codex: runtime `${CODEX_HOME}/config.toml` key `model`
- Gemini: runtime user-settings file `${GEMINI_CLI_HOME}/.gemini/settings.json` key path `model.name`

Normalized reasoning levels SHALL be projected through a Houmao-owned mapping policy layer instead of through one hard-coded cross-tool key. That mapping policy SHALL:

- accept the normalized reasoning level together with runtime context such as tool family, model name, and tool version when available,
- resolve the nearest supported native reasoning settings for that runtime,
- mutate only the constructed runtime home or launch environment for that build,
- preserve secret-free provenance describing the requested normalized level and the resolved native mapping.

Representative native target families SHALL include:

- Claude runtime effort or thinking-related settings such as `effortLevel`
- Codex runtime `${CODEX_HOME}/config.toml` key `model_reasoning_effort`
- Gemini runtime `${GEMINI_CLI_HOME}/.gemini/settings.json` generation settings under `modelConfigs` and `thinkingConfig`

#### Scenario: Claude model projection exports `ANTHROPIC_MODEL`
- **WHEN** the resolved model for one Claude runtime is `claude-sonnet-4-5`
- **THEN** the constructed Claude launch environment exports `ANTHROPIC_MODEL=claude-sonnet-4-5`
- **AND THEN** Houmao does not require the source auth bundle to be rewritten with that value

#### Scenario: Codex model projection patches the runtime `config.toml`
- **WHEN** the resolved model for one Codex runtime is `gpt-5.4`
- **THEN** the constructed Codex runtime home records `model = "gpt-5.4"` in its runtime `config.toml`
- **AND THEN** the reusable source setup bundle remains unchanged

#### Scenario: Gemini model projection patches runtime settings
- **WHEN** the resolved model for one Gemini runtime is `gemini-2.5-flash`
- **THEN** the constructed Gemini runtime home records `model.name = "gemini-2.5-flash"` in `${GEMINI_CLI_HOME}/.gemini/settings.json`
- **AND THEN** Houmao does not require the operator to pass a raw Gemini-specific startup flag manually

#### Scenario: Lowest normalized reasoning level maps to the lowest native setting
- **WHEN** the resolved launch-owned reasoning level for one runtime is `1`
- **THEN** Houmao projects the lowest native reasoning setting supported for that resolved tool/model combination
- **AND THEN** the manifest records both requested level `1` and the native resolved mapping summary

#### Scenario: Highest normalized reasoning level maps to the highest native setting
- **WHEN** the resolved launch-owned reasoning level for one runtime is `10`
- **THEN** Houmao projects the highest native reasoning setting supported for that resolved tool/model combination
- **AND THEN** the manifest records both requested level `10` and the native resolved mapping summary

#### Scenario: Intermediate normalized reasoning level may clamp to the nearest native bucket
- **WHEN** one tool/model combination supports fewer native reasoning buckets than the Houmao 1..10 scale
- **AND WHEN** the resolved launch-owned reasoning level is `7`
- **THEN** Houmao maps that request to the nearest native bucket defined by its mapping policy
- **AND THEN** the manifest records the requested normalized level and the resolved native bucket explicitly

### Requirement: Advanced vendor-native reasoning tuning remains outside the core CLI
The core launch/config CLI SHALL standardize only the model name and normalized reasoning level.

Detailed vendor-native reasoning controls that exceed that coarse abstraction, such as exact token budgets, generation-parameter recipes, or model-family-specific tuning tables, SHALL NOT become required first-class launch/config flags in this change.

The system MAY expose those advanced workflows through skills or other higher-level guidance instead of through the generic launch/config schema.
