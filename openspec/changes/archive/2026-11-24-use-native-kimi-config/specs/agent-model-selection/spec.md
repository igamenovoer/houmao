# Spec Delta

## MODIFIED Requirements

### Requirement: Kimi model selection projects through native model alias flag

Houmao SHALL resolve the selected Kimi model alias from effective native config and the existing launch model precedence. Headless and TUI startup SHALL pass explicit launch-owned selection as `--model <alias>`, including exact TUI continuation. ACP and Web SHALL project explicit selection into the runtime `default_model`. The selected alias SHALL resolve in native TOML.

#### Scenario: Kimi OAuth-backed launch emits model alias argument

- **WHEN** the resolved launch-owned model for a Kimi OAuth-backed prompt-mode runtime is `kimi-code/kimi-for-coding`
- **THEN** the managed Kimi command includes `--model kimi-code/kimi-for-coding`
- **AND THEN** the source credential config retains its authored default

#### Scenario: Kimi TUI launch emits model alias argument

- **WHEN** the resolved launch-owned model for a Kimi TUI runtime is `kimi-code/kimi-for-coding`
- **THEN** the final launch command includes `--model kimi-code/kimi-for-coding`
- **AND THEN** Kimi starts the interactive TUI with that alias

#### Scenario: Kimi TUI resumed launch keeps model alias argument

- **WHEN** Houmao relaunches a Kimi TUI session with explicit alias `kimi-code/kimi-for-coding` and exact session `session_abc`
- **THEN** the managed command includes `--model kimi-code/kimi-for-coding --session session_abc`

#### Scenario: Owned Kimi Web or ACP startup uses the selected alias

- **WHEN** an explicit launch model selects a declared alias different from the effective native `default_model` for Web or ACP
- **THEN** the private runtime config selects that declared alias as `default_model` before Kimi starts

#### Scenario: Kimi env-model conflict is handled explicitly

- **WHEN** a selected auth bundle or declared launch override supplies `KIMI_MODEL_NAME`
- **THEN** Houmao tells the operator to declare and select a native TOML alias before launch

#### Scenario: Kimi launch without model override preserves native baseline

- **WHEN** the effective Kimi config selects a default model and no recipe, profile, or one-shot launch input selects another model
- **THEN** the launched runtime uses the native default without requiring a Houmao model override

### Requirement: Kimi reasoning levels use selected-model effort capabilities

Kimi models with multiple selectable efforts SHALL declare ordered `support_efforts` in native TOML. After Kimi model overrides, positive Houmao levels SHALL select exact labels by position, starting at 1 and saturating at the last entry. Houmao SHALL project the selected label into native thinking config. Level 0 SHALL select off only when the native model permits it. Omission SHALL preserve native defaults.

#### Scenario: Kimi alias maps ordered efforts

- **WHEN** the selected Kimi alias declares effective efforts `low`, `high`, and `max`
- **AND WHEN** the launch-owned reasoning level is `2`
- **THEN** Houmao projects Kimi thinking enabled with effort `high`

#### Scenario: Two models give the same numeric level different meanings

- **WHEN** one alias declares `['brief', 'deliberate']` and another declares `['quick', 'extended', 'maximum']`
- **THEN** level `2` selects `deliberate` for the first alias and `extended` for the second
- **AND THEN** Houmao preserves the native names and their declared order without lowercasing or applying a cross-model vocabulary

#### Scenario: Kimi model overrides and saturation use the effective order

- **WHEN** a model overrides `support_efforts` with `['fast', 'Deep-Reasoning']` and the requested level is `5`
- **THEN** the native config receives `Deep-Reasoning`
- **AND THEN** launch provenance records requested level `5`, effective level `2`, and saturation

#### Scenario: Kimi missing effort metadata is rejected

- **WHEN** a positive level is requested and the selected native catalog is absent, empty, or malformed
- **THEN** Houmao reports the selected alias and `support_efforts` field with a correction diagnostic
- **AND THEN** Houmao does not invent a numeric-to-name mapping

#### Scenario: Kimi always-thinking models refuse off

- **WHEN** a caller requests level `0` for a Kimi model that requires thinking
- **THEN** Houmao rejects the request before startup or turn submission

#### Scenario: Native Kimi thinking defaults apply when no level is requested

- **WHEN** a Kimi launch selects an alias with native thinking preferences and no numeric override
- **THEN** its native defaults govern startup

#### Scenario: Kimi headless request override uses the selected alias and restores defaults

- **WHEN** a managed Kimi headless prompt supplies a request-scoped model and positive level
- **THEN** Houmao resolves the label from that alias in the committed runtime config and uses it for the turn
- **AND THEN** later turns use the runtime's prior default model and thinking settings
