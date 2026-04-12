## MODIFIED Requirements

### Requirement: Resolved model configuration is projected into tool-native runtime state
Before provider startup, the system SHALL project the resolved model configuration into the constructed runtime home, launch environment, or final provider CLI override arguments using supported tool-native startup surfaces.

At minimum, the maintained direct model-name projection targets SHALL be:

- Claude: launch environment variable `ANTHROPIC_MODEL`
- Codex: runtime `${CODEX_HOME}/config.toml` key `model` and final Codex CLI config override key `model`
- Gemini: runtime user-settings file `${GEMINI_CLI_HOME}/.gemini/settings.json` key path `model.name`

Reasoning preset indices SHALL be projected through a Houmao-owned mapping policy layer instead of through one hard-coded cross-tool key. That mapping policy SHALL:

- accept the requested reasoning preset index together with runtime context such as tool family, model name, and tool version when available,
- resolve the maintained ordered preset ladder for that runtime,
- map positive integers one increment per maintained preset step,
- map values above the maintained ladder length to the highest maintained preset for that runtime,
- accept `0` only when the resolved ladder supports an explicit off preset,
- support documented Houmao preset tables that may map one level to multiple native settings together,
- mutate only the constructed runtime home, launch environment, or final provider CLI override arguments for that build,
- preserve secret-free provenance describing the requested preset index, the resolved native mapping, whether saturation occurred, and whether final CLI override arguments were generated.

Representative native target families SHALL include:

- Claude runtime effort or thinking-related settings such as `effortLevel`
- Codex runtime `${CODEX_HOME}/config.toml` key `model_reasoning_effort` and final Codex CLI config override key `model_reasoning_effort`
- Gemini runtime `${GEMINI_CLI_HOME}/.gemini/settings.json` generation settings under `modelConfigs` and `thinkingConfig`

For Codex, generated runtime-home config projection SHALL remain present as fallback and inspection state, but the final Houmao-managed provider launch SHALL also include non-secret CLI config override arguments for resolved model-selection preferences so cwd/project `.codex/config.toml` cannot accidentally override them.

#### Scenario: Claude model projection exports `ANTHROPIC_MODEL`
- **WHEN** the resolved model for one Claude runtime is `claude-sonnet-4-5`
- **THEN** the constructed Claude launch environment exports `ANTHROPIC_MODEL=claude-sonnet-4-5`
- **AND THEN** Houmao does not require the source auth bundle to be rewritten with that value

#### Scenario: Codex model projection patches runtime config and emits CLI override
- **WHEN** the resolved model for one Codex runtime is `gpt-5.4`
- **THEN** the constructed Codex runtime home records `model = "gpt-5.4"` in its runtime `config.toml`
- **AND THEN** the Houmao-managed Codex launch includes a final CLI config override for `model = "gpt-5.4"`
- **AND THEN** the reusable source setup bundle remains unchanged

#### Scenario: Gemini model projection patches runtime settings
- **WHEN** the resolved model for one Gemini runtime is `gemini-2.5-flash`
- **THEN** the constructed Gemini runtime home records `model.name = "gemini-2.5-flash"` in `${GEMINI_CLI_HOME}/.gemini/settings.json`
- **AND THEN** Houmao does not require the operator to pass a raw Gemini-specific startup flag manually

#### Scenario: First positive reasoning preset maps to the first maintained native preset
- **WHEN** the resolved launch-owned reasoning level for one runtime is `1`
- **THEN** Houmao projects the first maintained native reasoning preset supported for that resolved tool/model combination
- **AND THEN** the manifest records both requested level `1` and the native resolved mapping summary

#### Scenario: Codex reasoning projection patches runtime config and emits CLI override
- **WHEN** the resolved launch-owned reasoning level for one Codex runtime maps to native `model_reasoning_effort = "low"`
- **THEN** the constructed Codex runtime home records `model_reasoning_effort = "low"` in its runtime `config.toml`
- **AND THEN** the Houmao-managed Codex launch includes a final CLI config override for `model_reasoning_effort = "low"`
- **AND THEN** a project-local `.codex/config.toml` value for `model_reasoning_effort` does not change the Houmao-managed launch's effective reasoning effort

#### Scenario: Reasoning value above the maintained ladder saturates to the highest native preset
- **WHEN** the resolved launch-owned reasoning level for one runtime is `12`
- **AND WHEN** the resolved tool/model ladder exposes only four positive maintained presets
- **THEN** Houmao projects the highest maintained native reasoning preset for that runtime
- **AND THEN** the manifest records the requested preset index together with saturation in the resolved native mapping summary

#### Scenario: Zero is rejected when the resolved runtime lacks an off preset
- **WHEN** the resolved launch-owned reasoning level for one runtime is `0`
- **AND WHEN** the resolved tool/model ladder does not support an explicit off preset
- **THEN** Houmao rejects that reasoning request clearly
- **AND THEN** it does not silently reinterpret `0` as the first positive preset

#### Scenario: Gemini preset can project to multiple native settings together
- **WHEN** one maintained Gemini preset row defines both a thinking level and a thinking budget for the resolved model family
- **AND WHEN** the resolved launch-owned reasoning level selects that preset row
- **THEN** Houmao projects the documented combination of native Gemini settings for that preset
- **AND THEN** the manifest records the resulting native mapping summary for the resolved runtime

## ADDED Requirements

### Requirement: Codex request-scoped execution overrides use CLI config overrides
For supported Codex headless prompt submission surfaces, request-scoped `execution.model` overrides SHALL be applied through final Codex CLI config override arguments in addition to any temporary runtime-home projection used for fallback or provenance.

Those request-scoped CLI config override arguments SHALL apply only to the accepted prompt being executed and SHALL NOT rewrite recipe, specialist, launch-profile, or later default execution state.

#### Scenario: Codex request-scoped reasoning override beats project config for one turn
- **WHEN** a managed Codex headless agent has a project-local `.codex/config.toml` that sets `model_reasoning_effort = "high"`
- **AND WHEN** a prompt request supplies `execution.model.reasoning.level = 2` that maps to `model_reasoning_effort = "low"`
- **THEN** the Codex headless turn command includes a final CLI config override for `model_reasoning_effort = "low"`
- **AND THEN** the accepted prompt uses the request-scoped reasoning effort instead of the project-local Codex config value
- **AND THEN** a later prompt that omits `execution.model` returns to the agent's launch-resolved default model configuration
