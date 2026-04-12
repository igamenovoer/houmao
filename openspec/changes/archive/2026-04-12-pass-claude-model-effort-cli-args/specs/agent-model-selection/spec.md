## MODIFIED Requirements

### Requirement: Resolved model configuration is projected into tool-native runtime state
Before provider startup, the system SHALL project the resolved model configuration into the constructed runtime home, launch environment, or final provider CLI override arguments using supported tool-native startup surfaces.

At minimum, the maintained direct model-name projection targets SHALL be:

- Claude: final Claude CLI argument `--model <name>` for Houmao-managed provider startup when the resolved model name comes from a launch-owned layer above copied native baseline
- Codex: runtime `${CODEX_HOME}/config.toml` key `model` and final Codex CLI config override key `model`
- Gemini: runtime user-settings file `${GEMINI_CLI_HOME}/.gemini/settings.json` key path `model.name`

Claude auth-bundle or copied native baseline env vars such as `ANTHROPIC_MODEL`, `ANTHROPIC_DEFAULT_OPUS_MODEL`, `ANTHROPIC_DEFAULT_SONNET_MODEL`, `ANTHROPIC_DEFAULT_HAIKU_MODEL`, `ANTHROPIC_SMALL_FAST_MODEL`, and `CLAUDE_CODE_SUBAGENT_MODEL` SHALL remain supported as baseline or native-provider inputs, but launch-owned Claude model overrides SHALL NOT depend on projecting a new `ANTHROPIC_MODEL` value into the final provider process.

Reasoning preset indices SHALL be projected through a Houmao-owned mapping policy layer instead of through one hard-coded cross-tool key. That mapping policy SHALL:

- accept the requested reasoning preset index together with runtime context such as tool family, model name, and tool version when available,
- resolve the maintained ordered preset ladder for that runtime,
- map positive integers one increment per maintained preset step,
- map values above the maintained ladder length to the highest maintained preset for that runtime,
- accept `0` only when the resolved ladder supports an explicit off preset,
- support documented Houmao preset tables that may map one level to multiple native settings together,
- mutate only the constructed runtime home, launch environment, or final provider CLI override arguments for that build,
- preserve secret-free provenance describing the requested preset index, the resolved native mapping, whether saturation occurred, and whether final CLI override arguments were generated.

Codex reasoning mapping SHALL use a maintained model-aware ladder rather than treating every value in Codex's generic reasoning-effort enum as supported by every Codex model.

For current maintained Codex coding models such as `gpt-5.4`, `gpt-5.3-codex`, and `gpt-5.2-codex`, the positive Codex reasoning ladder SHALL be:

- `1=low`
- `2=medium`
- `3=high`
- `4=xhigh`

Higher positive values for those Codex model ladders SHALL saturate to `xhigh`.

`minimal` SHALL NOT be projected for a resolved Codex model unless that model's maintained ladder explicitly includes `minimal`.

Representative native target families SHALL include:

- Claude final CLI effort argument `--effort <level>` for maintained Claude effort values such as `low`, `medium`, `high`, and `max`
- Codex runtime `${CODEX_HOME}/config.toml` key `model_reasoning_effort` and final Codex CLI config override key `model_reasoning_effort`
- Gemini runtime `${GEMINI_CLI_HOME}/.gemini/settings.json` generation settings under `modelConfigs` and `thinkingConfig`

For Codex, generated runtime-home config projection SHALL remain present as fallback and inspection state, but the final Houmao-managed provider launch SHALL also include non-secret CLI config override arguments for resolved model-selection preferences so cwd/project `.codex/config.toml` cannot accidentally override them.

For Claude, generated runtime-home settings MAY remain present as fallback and inspection state, but the final Houmao-managed provider launch SHALL include non-secret CLI arguments for resolved launch-owned model-selection preferences so tmux, headless, or other provider-startup paths cannot accidentally drop those preferences through environment propagation gaps.

#### Scenario: Claude model projection emits final CLI argument
- **WHEN** the resolved launch-owned model for one Claude runtime is `sonnet`
- **THEN** the Houmao-managed Claude provider launch includes final CLI arguments `--model sonnet`
- **AND THEN** Houmao does not require the source auth bundle to be rewritten with that value
- **AND THEN** the launched Claude process does not depend on a newly projected `ANTHROPIC_MODEL=sonnet` environment variable to honor the launch-owned override

#### Scenario: Claude effort projection emits final CLI argument
- **WHEN** the resolved launch-owned reasoning level for one Claude runtime maps to native effort `high`
- **THEN** the Houmao-managed Claude provider launch includes final CLI arguments `--effort high`
- **AND THEN** the constructed runtime home or manifest records secret-free provenance for the requested reasoning level and resolved effort value

#### Scenario: Claude TUI honors source-level Sonnet preference
- **WHEN** a Claude specialist stores default model `sonnet`
- **AND WHEN** a local interactive TUI instance is launched from that specialist without a higher-priority model override
- **THEN** the final Claude TUI launch command includes `--model sonnet`
- **AND THEN** Claude starts with the Sonnet model even when the account's native default model would otherwise be Opus

#### Scenario: Claude headless honors direct model and effort overrides
- **WHEN** a Claude headless launch receives direct overrides `--model sonnet --reasoning-level 3`
- **AND WHEN** the resolved Claude reasoning ladder maps level `3` to effort `high`
- **THEN** the final Claude headless provider command includes `--model sonnet --effort high`
- **AND THEN** the direct overrides apply only to that launch and do not rewrite the reusable specialist, recipe, launch-profile, or auth-bundle state

#### Scenario: Claude auth-bundle model env remains baseline input
- **WHEN** the selected Claude auth bundle or copied native state provides `ANTHROPIC_MODEL=opus`
- **AND WHEN** no source, launch-profile, or direct launch-owned model override is supplied
- **THEN** the launched Claude runtime may use that native baseline model value
- **AND THEN** Houmao does not require the operator to migrate the auth bundle to a unified launch-owned model field before launch succeeds

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

#### Scenario: Current Codex coding model first preset maps to low
- **WHEN** the resolved tool is `codex`
- **AND WHEN** the resolved model is `gpt-5.4`
- **AND WHEN** the resolved launch-owned reasoning level is `1`
- **THEN** Houmao projects native `model_reasoning_effort = "low"`
- **AND THEN** Houmao does not project native `model_reasoning_effort = "minimal"`

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
