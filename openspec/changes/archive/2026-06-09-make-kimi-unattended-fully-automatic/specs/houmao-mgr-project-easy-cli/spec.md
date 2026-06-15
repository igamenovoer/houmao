## ADDED Requirements

### Requirement: Project-backed Kimi unattended launch delegates to maintained automatic posture
When a selected Kimi specialist or Kimi-backed project profile resolves `launch.prompt_mode: unattended`, `houmao-mgr project agents launch` SHALL delegate to the managed native launch path in a way that lets downstream Kimi launch policy and runtime force Kimi auto permission mode.

For Kimi specialists and profiles, unattended prompt mode SHALL NOT imply headless launch. If the operator does not request `--headless`, Kimi SHALL remain eligible for the maintained local-interactive TUI backend while still receiving the maintained no-question unattended posture.

When a selected Kimi specialist or Kimi-backed project profile resolves `launch.prompt_mode: as_is`, project launch SHALL preserve as-is behavior and SHALL NOT inject a separate provider auto, yolo, or unattended override.

#### Scenario: Kimi project specialist launches TUI unattended automatically
- **WHEN** a project specialist `writer` exists with tool `kimi` and stored `launch.prompt_mode: unattended`
- **AND WHEN** an operator runs `houmao-mgr project agents launch --specialist writer --name writer-1` without `--headless`
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
