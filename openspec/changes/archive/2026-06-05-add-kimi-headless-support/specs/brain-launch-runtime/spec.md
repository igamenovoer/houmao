## ADDED Requirements

### Requirement: Kimi headless backend via prompt-mode stream JSON
For Kimi, the system SHALL support a non-CAO interactive backend using repeated Kimi Code CLI prompt-mode invocations with machine-readable stream JSON output and session resume.

The runtime SHALL:

- start a new Kimi headless turn using `kimi -p <prompt> --output-format stream-json`,
- capture the returned Kimi `session_id` from the `session.resume_hint` meta event,
- persist that `session_id` in the session manifest,
- resume subsequent turns in the same recorded working directory using `--session <session_id>`,
- continue the previous Kimi session for a working directory using `--continue` when caller explicitly requests latest-or-new selection, and
- avoid adding prompt-mode-incompatible Kimi flags such as `--auto`, `--yolo`, or `--plan`.

#### Scenario: First Kimi headless turn persists the returned session id
- **WHEN** a developer starts a Kimi headless session and sends a first prompt using a constructed brain home
- **THEN** the runtime invokes Kimi using prompt mode and `--output-format stream-json`
- **AND THEN** the runtime extracts the Kimi `session_id` from the stream JSON resume-hint meta event
- **AND THEN** the runtime persists that `session_id` in the session manifest

#### Scenario: Follow-up Kimi turn resumes by exact persisted session id
- **WHEN** a developer sends a follow-up prompt to a Kimi headless session
- **AND WHEN** the session manifest contains a persisted Kimi `session_id`
- **THEN** the runtime invokes Kimi with `--session <session_id>` before `-p <prompt>`
- **AND THEN** the runtime does not use bare `--session`, `--continue`, or latest-session selection for that exact follow-up turn

#### Scenario: Kimi prompt argument is placed next to the prompt flag
- **WHEN** the runtime builds a Kimi headless command for a new or resumed turn
- **THEN** the effective prompt value is passed immediately after `-p` or `--prompt`
- **AND THEN** resume selector args appear before the prompt flag rather than between the prompt flag and its value

#### Scenario: Kimi resume uses the recorded project context
- **WHEN** a developer resumes a Kimi headless session from a persisted session manifest
- **THEN** the resumed turn uses the same working directory recorded in the session manifest
- **AND THEN** the runtime returns an explicit error instead of silently resuming from a different project context

### Requirement: Kimi managed runtime homes support OAuth and env-model credentials
When the runtime constructs a Kimi headless home, the system SHALL support non-interactive startup from Kimi OAuth-backed credential material and Kimi env-model credential material.

The Kimi runtime home SHALL use `KIMI_CODE_HOME` as the provider home selector.

For OAuth-backed homes, Houmao SHALL project the Kimi config and token storage needed by Kimi Code prompt mode, including `config.toml` and `credentials/kimi-code.json` when present in the selected auth bundle.

For env-model homes, Houmao SHALL project allowlisted `KIMI_MODEL_*` environment variables needed by Kimi Code env-model startup.

#### Scenario: Kimi OAuth launch projects config and credentials into the runtime home
- **WHEN** the runtime builds a Kimi headless home from an OAuth-backed auth bundle that provides `config.toml` and `credentials/kimi-code.json`
- **THEN** the launched Kimi process receives `KIMI_CODE_HOME` pointing at the constructed runtime home
- **AND THEN** Kimi can read the projected config and OAuth token storage without depending on the operator's user-global `~/.kimi-code`

#### Scenario: Kimi env-model launch receives allowlisted model environment
- **WHEN** the runtime builds a Kimi headless home from an env-model auth bundle that provides `KIMI_MODEL_NAME` and `KIMI_MODEL_API_KEY`
- **THEN** the launched Kimi process receives those allowlisted environment variables
- **AND THEN** the first Kimi headless turn can start non-interactively without requiring a projected OAuth token file

### Requirement: Kimi managed skill projection is deterministic
When Houmao projects skills into a managed Kimi home, the system SHALL use `<KIMI_CODE_HOME>/skills` as the managed Kimi skills root and SHALL pass that root to Kimi prompt mode through `--skills-dir`.

Managed Kimi launches SHALL NOT depend on Kimi's default user-global skill discovery from `~/.agents/skills`.

#### Scenario: Constructed Kimi home loads only the managed skills root
- **WHEN** the runtime builds a Kimi managed home with one or more selected skills
- **THEN** the selected skills are projected under `<KIMI_CODE_HOME>/skills`
- **AND THEN** the Kimi headless launch includes `--skills-dir <KIMI_CODE_HOME>/skills`
- **AND THEN** the managed launch does not require user-global `~/.agents/skills` to be present
