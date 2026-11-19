# Spec Delta

## ADDED Requirements

### Requirement: Kimi project launch resolves its run mode through the shared selector

Project birth for Kimi SHALL select tui when no stored mode or direct override applies. Direct `--mode headless` SHALL select `kimi_headless`. Other explicit modes SHALL require a qualified Kimi adapter. The maintained native tool set governs provider validation.

#### Scenario: Kimi specialist launches with its default

- **WHEN** a project launches a Kimi specialist without a stored or direct mode
- **THEN** the native tool starts with local_interactive in tui mode

#### Scenario: Kimi project profile launches with its default

- **WHEN** a project launches a Kimi profile that omits mode and the caller also omits it
- **THEN** the manager delegates to the maintained Kimi TUI

#### Scenario: Explicit Kimi headless launch remains supported

- **WHEN** an operator passes `--mode headless` to a Kimi specialist launch
- **THEN** the manager launches the one-shot `kimi_headless` backend

#### Scenario: Removed providers are rejected

- **WHEN** a project selects a provider outside the maintained native tool set
- **THEN** the project launch fails before provider startup for every run mode

## MODIFIED Requirements

### Requirement: Project-backed Kimi unattended launch delegates to maintained automatic posture
When a selected Kimi specialist or Kimi-backed project profile resolves `launch.prompt_mode: unattended`, `houmao-mgr project agents launch` SHALL delegate to the managed native launch path in a way that lets downstream Kimi launch policy and runtime force Kimi auto permission mode.

For Kimi specialists and profiles, unattended prompt mode SHALL NOT imply headless launch. Kimi project launch SHALL apply unattended policy to the selected run mode. With no selected mode, the maintained TUI remains the project default.

When a selected Kimi specialist or Kimi-backed project profile resolves `launch.prompt_mode: as_is`, project launch SHALL preserve as-is behavior and SHALL NOT inject a separate provider auto, yolo, or unattended override.

#### Scenario: Kimi project specialist launches TUI unattended automatically
- **WHEN** a project specialist `writer` exists with tool `kimi` and stored `launch.prompt_mode: unattended`
- **AND WHEN** an operator runs `houmao-mgr project agents launch --specialist writer --name writer-1` without a mode override
- **THEN** the command delegates to native launch with Kimi local-interactive posture
- **AND THEN** the resulting launch resolves the maintained Kimi unattended local-interactive policy

#### Scenario: Kimi project profile launches TUI unattended automatically
- **WHEN** project profile `writer-profile` targets a Kimi specialist and stores prompt mode `unattended`
- **AND WHEN** an operator runs `houmao-mgr project agents launch --profile writer-profile`
- **THEN** the command delegates to native launch with the stored unattended prompt mode
- **AND THEN** the resulting Kimi TUI launch is expected to run without tool approval or user-question prompts

#### Scenario: Kimi as-is project launch remains manual
- **WHEN** a project specialist `writer` exists with tool `kimi` and stored `launch.prompt_mode: as_is`
- **AND WHEN** an operator runs `houmao-mgr project agents launch --specialist writer --name writer-1`
- **THEN** the command delegates to native launch with as-is prompt mode
- **AND THEN** it does not request Kimi auto permission mode through launch policy or runtime startup refresh

## REMOVED Requirements

### Requirement: Kimi project agents launch through local interactive posture by default

**Reason**: The four-mode project selector and current provider set replace the old Boolean and removed-provider exception.

**Migration**: Omit the selector for Kimi's project default or choose an explicitly qualified Kimi mode.
