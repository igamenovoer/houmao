## ADDED Requirements

### Requirement: Houmao-launched tmux sessions inject interactive terminal defaults
Houmao-created tmux sessions SHALL apply a Houmao-owned configuration overlay by default after tmux has loaded the user's normal configuration.

The overlay SHALL enable mouse mode for the launched session and SHALL configure rich color support for the launched tmux surface.

The overlay SHALL only set the tmux options and session environment values Houmao explicitly owns for this behavior, and SHALL leave unrelated user tmux configuration values unchanged.

The overlay SHALL be disabled when `HOUMAO_ENABLE_TMUX_CONFIG_INJECTION=0` is present in the launching environment.

#### Scenario: Launched session receives mouse and rich-color defaults
- **WHEN** Houmao creates a tmux-backed managed-agent session
- **AND WHEN** `HOUMAO_ENABLE_TMUX_CONFIG_INJECTION` is unset
- **THEN** Houmao applies its tmux configuration overlay after creating the session
- **AND THEN** the launched session has mouse mode enabled
- **AND THEN** the launched session advertises a 256-color tmux terminal with true-color capability for provider processes

#### Scenario: User configuration remains otherwise intact
- **WHEN** the user's tmux configuration defines options unrelated to Houmao's mouse and rich-color overlay
- **AND WHEN** Houmao creates a tmux-backed managed-agent session
- **THEN** Houmao does not clear or rewrite those unrelated tmux options
- **AND THEN** only the Houmao-owned mouse, terminal identity, true-color, and color environment values are overlaid

#### Scenario: Environment opt-out disables injection
- **WHEN** the launching environment contains `HOUMAO_ENABLE_TMUX_CONFIG_INJECTION=0`
- **AND WHEN** Houmao creates a tmux-backed managed-agent session
- **THEN** Houmao does not apply its tmux configuration overlay
- **AND THEN** Houmao preserves the existing launch environment color behavior instead of forcing rich-color defaults

### Requirement: Houmao launch environment removes inherited color suppression when injection is enabled
When tmux configuration injection is enabled, Houmao SHALL publish terminal color environment values into launched tmux sessions that support rich color output.

The published environment SHALL set `TERM=tmux-256color`, set `COLORTERM=truecolor`, and prevent inherited `NO_COLOR` from suppressing color in managed provider processes.

The published environment SHALL preserve unrelated inherited and launch-specific environment values.

#### Scenario: Inherited NO_COLOR does not suppress managed session color
- **WHEN** the launching process has `NO_COLOR=1`
- **AND WHEN** `HOUMAO_ENABLE_TMUX_CONFIG_INJECTION` is unset
- **AND WHEN** Houmao launches a tmux-backed managed-agent session
- **THEN** the launched provider environment does not contain `NO_COLOR`
- **AND THEN** the launched provider environment contains `TERM=tmux-256color`
- **AND THEN** the launched provider environment contains `COLORTERM=truecolor`

#### Scenario: Unrelated environment values are preserved
- **WHEN** the launching process has an unrelated environment variable `EXAMPLE_TOKEN=abc`
- **AND WHEN** Houmao launches a tmux-backed managed-agent session with tmux configuration injection enabled
- **THEN** the launched provider environment still contains `EXAMPLE_TOKEN=abc`
- **AND THEN** Houmao only changes the color-related environment variables it owns for the injection behavior

### Requirement: Tmux configuration injection failures guide operator recovery
If Houmao creates a tmux session but cannot apply the enabled tmux configuration injection, the launch SHALL fail with an error that identifies tmux configuration injection as the failing step.

The error SHALL include guidance that the operator can retry with `HOUMAO_ENABLE_TMUX_CONFIG_INJECTION=0` to disable the overlay.

When practical, Houmao SHALL clean up the newly-created tmux session before returning the launch failure.

#### Scenario: Injection failure reports opt-out guidance
- **WHEN** Houmao creates tmux session `S`
- **AND WHEN** the tmux configuration injection command fails
- **THEN** the launch fails with an error that names tmux configuration injection
- **AND THEN** the error includes `HOUMAO_ENABLE_TMUX_CONFIG_INJECTION=0` as the disablement mechanism
- **AND THEN** Houmao attempts to remove tmux session `S`
