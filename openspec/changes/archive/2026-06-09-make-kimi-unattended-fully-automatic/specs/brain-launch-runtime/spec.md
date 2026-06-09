## ADDED Requirements

### Requirement: Kimi unattended local-interactive launch runs in automatic no-question mode
When a Kimi Code local-interactive launch resolves `operator_prompt_mode = unattended`, the runtime SHALL start the provider in Kimi auto permission mode before submitting any Houmao role bootstrap, mailbox notification, or workload prompt.

For fresh Kimi TUI sessions, the runtime SHALL rely on the launch-policy-owned managed runtime-home config value `default_permission_mode = "auto"` as the provider-native fresh-session default.

For resumed Kimi TUI sessions or existing provider sessions whose stored permission may not be auto, the runtime SHALL refresh Kimi permission mode by issuing the provider-native `/auto on` TUI command before managed prompts are submitted.

Kimi unattended local-interactive launch SHALL NOT add `--auto`, `--yolo`, or `--plan` to Kimi TUI startup commands that include `--continue` or `--session <session_id>`.

If the runtime cannot force or refresh Kimi auto mode for an unattended local-interactive launch, the launch or relaunch SHALL fail clearly rather than proceeding in manual approval mode.

When a Kimi Code local-interactive launch resolves `operator_prompt_mode = as_is`, the runtime SHALL NOT force Kimi auto permission mode and SHALL leave provider approval behavior to the launched Kimi session.

#### Scenario: Fresh unattended Kimi TUI launch starts in auto mode
- **WHEN** a managed Kimi Code local-interactive launch resolves `operator_prompt_mode = unattended`
- **AND WHEN** no provider-native session resume selector is used
- **THEN** the launch policy writes `default_permission_mode = "auto"` in the managed Kimi runtime home before provider start
- **AND THEN** the runtime does not submit the Houmao role bootstrap or workload prompt until the TUI startup path is expected to be in auto mode

#### Scenario: Resumed unattended Kimi TUI launch refreshes auto mode
- **WHEN** a managed Kimi Code local-interactive relaunch resolves `operator_prompt_mode = unattended`
- **AND WHEN** the relaunch resumes provider history with `--continue` or `--session <session_id>`
- **THEN** the runtime does not add `--auto` to the Kimi startup command
- **AND THEN** after Kimi TUI readiness, the runtime issues `/auto on` before any managed workload prompt

#### Scenario: Auto refresh failure blocks unattended launch
- **WHEN** a managed Kimi Code local-interactive launch resolves `operator_prompt_mode = unattended`
- **AND WHEN** the runtime cannot submit or confirm the startup auto-mode refresh required for that launch path
- **THEN** the launch or relaunch fails with a diagnostic that names Kimi unattended auto-mode setup
- **AND THEN** the runtime does not continue into a manual approval posture

#### Scenario: As-is Kimi TUI remains manual when provider chooses manual
- **WHEN** a managed Kimi Code local-interactive launch resolves `operator_prompt_mode = as_is`
- **THEN** the runtime does not write `default_permission_mode = "auto"` as launch-policy-owned state
- **AND THEN** the runtime does not issue `/auto on` before managed prompts

#### Scenario: Kimi auto mode is no-question but not hard-deny bypass
- **WHEN** Kimi unattended local-interactive launch has entered Kimi auto permission mode
- **THEN** Kimi tool approval prompts and `AskUserQuestion` requests do not require operator input during normal agent work
- **AND THEN** Kimi may still block work through explicit provider hard-deny policies or user-configured deny rules
