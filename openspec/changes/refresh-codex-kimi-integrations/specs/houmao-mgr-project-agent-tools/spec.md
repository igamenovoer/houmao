## ADDED Requirements

### Requirement: Starter Kimi environment projection matches current Kimi Code model variables
The starter Kimi adapter SHALL allow current Kimi Code model variables needed for managed model, reasoning, sampling, and output-limit configuration. The allowlist SHALL include `KIMI_MODEL_THINKING_KEEP`, `KIMI_MODEL_TEMPERATURE`, `KIMI_MODEL_TOP_P`, `KIMI_MODEL_MAX_TOKENS`, and `KIMI_MODEL_MAX_COMPLETION_TOKENS`.

The starter adapter SHALL remove obsolete `KIMI_MODEL_DEFAULT_THINKING` and `KIMI_MODEL_THINKING_MODE` entries. Existing current provider, endpoint, credential, capability, and thinking-effort variables SHALL remain available.

#### Scenario: Current Kimi thinking and sampling variables survive projection
- **WHEN** a Kimi env-model auth bundle supplies current thinking, sampling, or output-limit variables
- **THEN** the managed Kimi runtime receives the allowlisted values

#### Scenario: Obsolete Kimi thinking variables are not advertised
- **WHEN** a maintainer inspects the starter Kimi adapter
- **THEN** it does not list `KIMI_MODEL_DEFAULT_THINKING` or `KIMI_MODEL_THINKING_MODE`

