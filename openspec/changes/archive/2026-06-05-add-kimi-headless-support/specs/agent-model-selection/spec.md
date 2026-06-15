## ADDED Requirements

### Requirement: Kimi model selection projects through native model alias flag
When the resolved launch-owned model configuration supplies a Kimi model name for a managed Kimi runtime, the system SHALL project that model name through Kimi's native startup surface for prompt mode.

For config-backed or OAuth-backed Kimi homes, Houmao SHALL pass final CLI arguments `--model <alias>` for the resolved launch-owned model name.

For env-model Kimi homes, Houmao SHALL either project the model name by updating the launched process's `KIMI_MODEL_NAME` environment value or reject unsupported model override combinations clearly before provider start.

#### Scenario: Kimi OAuth-backed launch emits model alias argument
- **WHEN** the resolved launch-owned model for one OAuth-backed Kimi runtime is `kimi-code/kimi-for-coding`
- **THEN** the Houmao-managed Kimi provider launch includes final CLI arguments `--model kimi-code/kimi-for-coding`
- **AND THEN** Houmao does not require the source auth bundle to be rewritten with that value

#### Scenario: Kimi env-model conflict is handled explicitly
- **WHEN** the selected Kimi auth bundle uses `KIMI_MODEL_NAME`
- **AND WHEN** a higher-priority launch-owned model override is supplied
- **THEN** Houmao either updates the launched process's `KIMI_MODEL_NAME` to the resolved model value or rejects the launch with a clear unsupported-combination error
- **AND THEN** Houmao does not silently pass a `--model` alias that the env-model configuration cannot resolve

#### Scenario: Kimi launch without model override preserves native baseline
- **WHEN** copied Kimi config or auth state already selects a default model
- **AND WHEN** no recipe, launch-profile, or direct launch-owned model override is supplied
- **THEN** the launched Kimi runtime may use that native baseline model value
- **AND THEN** Houmao does not require the operator to backfill a unified model field before launch succeeds
