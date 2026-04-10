## MODIFIED Requirements

### Requirement: Unified model configuration is launch-owned and secret-free
The system SHALL expose a tool-agnostic model-configuration field as launch configuration rather than as auth-owned or setup-owned user-facing state.

Recipes or specialists MAY persist a default model name.

Recipes, specialists, or launch profiles MAY also persist an optional reasoning preset index as part of that same launch-owned model configuration.

Launch profiles MAY persist reusable model and reasoning overrides.

Direct launch surfaces MAY provide one-off model and reasoning overrides.

The reasoning field SHALL be a non-negative integer interpreted relative to the resolved tool and resolved model rather than as a normalized portable `1..10` scale.

`0` SHALL mean explicit off or no-thinking only when the resolved tool/model ladder supports such a preset and SHALL otherwise be rejected clearly instead of being silently promoted to the first positive preset.

Positive integers SHALL refer to the first, second, and later maintained reasoning presets for the resolved tool/model ladder.

There SHALL be no global upper bound shared across tools.

This field SHALL remain secret-free and SHALL NOT require operators to author tool-specific env vars, auth-bundle values, or setup-file edits directly.

Persistent env authoring surfaces SHALL NOT become the supported way to specify the model-configuration field.

#### Scenario: Source and profile defaults are treated as launch configuration
- **WHEN** a recipe stores default model `gpt-5.4` with reasoning level `6`
- **AND WHEN** a launch profile stores default model `gpt-5.4-mini` with reasoning level `4`
- **THEN** Houmao persists those values as launch-owned configuration
- **AND THEN** neither value is treated as inline credential material

#### Scenario: Negative reasoning level is rejected clearly
- **WHEN** an operator attempts to author reasoning level `-1`
- **THEN** the system rejects the value clearly
- **AND THEN** the accepted reasoning-level domain remains non-negative integers only

#### Scenario: Stored reasoning value is not constrained by a portable upper bound
- **WHEN** an operator attempts to author reasoning level `12`
- **THEN** the system accepts that value as launch-owned configuration when the surrounding model configuration is otherwise valid
- **AND THEN** Houmao does not reject it only because it exceeds a portable `1..10` range

### Requirement: Resolved model configuration is projected into tool-native runtime state
Before provider startup, the system SHALL project the resolved model configuration into the constructed runtime home or launch environment using supported tool-native startup surfaces.

At minimum, the maintained direct model-name projection targets SHALL be:

- Claude: launch environment variable `ANTHROPIC_MODEL`
- Codex: runtime `${CODEX_HOME}/config.toml` key `model`
- Gemini: runtime user-settings file `${GEMINI_CLI_HOME}/.gemini/settings.json` key path `model.name`

Reasoning preset indices SHALL be projected through a Houmao-owned mapping policy layer instead of through one hard-coded cross-tool key. That mapping policy SHALL:

- accept the requested reasoning preset index together with runtime context such as tool family, model name, and tool version when available,
- resolve the maintained ordered preset ladder for that runtime,
- map positive integers one increment per maintained preset step,
- map values above the maintained ladder length to the highest maintained preset for that runtime,
- accept `0` only when the resolved ladder supports an explicit off preset,
- support documented Houmao preset tables that may map one level to multiple native settings together,
- mutate only the constructed runtime home or launch environment for that build,
- preserve secret-free provenance describing the requested preset index, the resolved native mapping, and whether saturation occurred.

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

#### Scenario: First positive reasoning preset maps to the first maintained native preset
- **WHEN** the resolved launch-owned reasoning level for one runtime is `1`
- **THEN** Houmao projects the first maintained native reasoning preset supported for that resolved tool/model combination
- **AND THEN** the manifest records both requested level `1` and the native resolved mapping summary

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

### Requirement: Advanced vendor-native reasoning tuning remains outside the core CLI
The core launch/config CLI SHALL standardize only the model name and the tool/model-relative reasoning preset index.

Detailed vendor-native reasoning controls that exceed that coarse abstraction, such as exact token budgets, generation-parameter recipes, or model-family-specific tuning tables, SHALL NOT become required first-class launch/config flags in this change.

The system MAY expose those advanced workflows through skills or other higher-level guidance instead of through the generic launch/config schema.

When an operator needs finer control than a maintained Houmao preset ladder provides, the supported workflow SHALL be to omit Houmao `reasoning.level` and manage native tool config or env directly.

#### Scenario: Provider-specific reasoning controls stay outside generic launch flags
- **WHEN** an operator needs advanced provider-native reasoning controls such as exact Gemini thinking budgets or model-family-specific tuning tables
- **THEN** the core Houmao launch and configuration surfaces continue exposing only the model name and reasoning preset index
- **AND THEN** the workflow is handled by omitting Houmao reasoning-level and using higher-level guidance or native tool configuration instead of new generic CLI flags

### Requirement: Headless prompt submission reuses the unified model configuration as a request-scoped execution override
For supported headless prompt submission surfaces, the system SHALL accept an optional request-scoped `execution.model` object that reuses the same model-configuration shape as launch-owned model selection.

`execution.model.name` SHALL use the same model-name field as launch-owned model selection.

`execution.model.reasoning.level` SHALL use the same non-negative tool/model-relative preset-index semantics as launch-owned model selection.

When a request supplies only one of `name` or `reasoning`, omitted subfields SHALL inherit from the addressed agent's launch-resolved effective model configuration for that prompt.

The request-scoped override SHALL apply only to the accepted headless prompt submission being executed.

The request-scoped override SHALL NOT rewrite copied baseline state, recipe state, specialist state, launch-profile state, runtime manifests, or later default execution state.

#### Scenario: Model-only request override inherits the launch-resolved reasoning level
- **WHEN** a managed headless agent has launch-resolved model `gpt-5.4` with reasoning level `6`
- **AND WHEN** the caller submits a headless prompt request with `execution.model.name = "gpt-5.4-mini"` and no request reasoning override
- **THEN** the effective model for that accepted prompt is `gpt-5.4-mini`
- **AND THEN** the effective reasoning level for that accepted prompt remains `6`

#### Scenario: Reasoning-only request override inherits the launch-resolved model name
- **WHEN** a managed headless agent has launch-resolved model `gpt-5.4` with reasoning level `6`
- **AND WHEN** the caller submits a headless prompt request with `execution.model.reasoning.level = 3` and no request model-name override
- **THEN** the effective model for that accepted prompt remains `gpt-5.4`
- **AND THEN** the effective reasoning level for that accepted prompt is `3`

#### Scenario: Request-scoped override does not become the next prompt default
- **WHEN** a managed headless agent has launch-resolved model `gpt-5.4`
- **AND WHEN** one accepted prompt runs with request override `execution.model.name = "gpt-5.4-mini"`
- **AND WHEN** a later accepted prompt omits `execution.model`
- **THEN** the later prompt uses the agent's normal launch-resolved default model
- **AND THEN** the earlier request override does not remain as live execution state

#### Scenario: Negative request reasoning is rejected
- **WHEN** a caller submits a headless prompt request with `execution.model.reasoning.level = -1`
- **THEN** the system rejects that request clearly
- **AND THEN** the accepted request-scoped reasoning domain remains non-negative integers only

#### Scenario: Request-scoped zero is rejected when the resolved runtime lacks an off preset
- **WHEN** a managed headless agent resolves to a tool/model ladder without an explicit off preset
- **AND WHEN** the caller submits a headless prompt request with `execution.model.reasoning.level = 0`
- **THEN** the system rejects that request clearly
- **AND THEN** it does not silently reinterpret `0` as the first positive preset
