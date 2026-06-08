## MODIFIED Requirements

### Requirement: Kimi model selection projects through native model alias flag
When the resolved launch-owned model configuration supplies a Kimi model name for a managed Kimi runtime, the system SHALL project that model name through Kimi's native startup surface for prompt-mode and TUI launches.

For config-backed or OAuth-backed Kimi homes, Houmao SHALL pass final CLI arguments `--model <alias>` for the resolved launch-owned model name.

For Kimi TUI relaunch that resumes a provider chat with `--continue` or `--session <session_id>`, Houmao SHALL preserve the resolved launch-owned `--model <alias>` argument because Kimi accepts model selection with resumed TUI startup.

For env-model Kimi homes, Houmao SHALL either project the model name by updating the launched process's `KIMI_MODEL_NAME` environment value or reject unsupported model override combinations clearly before provider start.

#### Scenario: Kimi OAuth-backed launch emits model alias argument
- **WHEN** the resolved launch-owned model for one OAuth-backed Kimi runtime is `kimi-code/kimi-for-coding`
- **THEN** the Houmao-managed Kimi provider launch includes final CLI arguments `--model kimi-code/kimi-for-coding`
- **AND THEN** Houmao does not require the source auth bundle to be rewritten with that value

#### Scenario: Kimi TUI launch emits model alias argument
- **WHEN** the resolved launch-owned model for one OAuth-backed Kimi local interactive runtime is `kimi-code/kimi-for-coding`
- **THEN** the Houmao-managed Kimi TUI launch command includes final CLI arguments `--model kimi-code/kimi-for-coding`
- **AND THEN** Kimi starts the interactive TUI with the launch-owned model selection

#### Scenario: Kimi TUI resumed launch keeps model alias argument
- **WHEN** the resolved launch-owned model for one OAuth-backed Kimi local interactive runtime is `kimi-code/kimi-for-coding`
- **AND WHEN** the runtime relaunches that session with Kimi exact-session selector `session_abc`
- **THEN** the Houmao-managed Kimi TUI relaunch command includes `--model kimi-code/kimi-for-coding --session session_abc`
- **AND THEN** Houmao does not strip model selection solely because the relaunch resumes a provider chat

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
