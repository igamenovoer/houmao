# Headless Output Rendering Delta

## ADDED Requirements

### Requirement: Headless project instances record and reuse their effective display settings

A headless project launch SHALL record effective `headless_display_style` and `headless_display_detail` in `launch_plan.metadata`. The live tmux bridge SHALL render managed turns using those values. Resume and relaunch SHALL recover both values from the instance manifest, using the built-in default for a missing field in a supported manifest.

#### Scenario: The pane uses the resolved launch configuration

- **WHEN** a project launch resolves style `plain` and detail `detail` and a managed turn produces canonical reasoning text
- **THEN** the manifest records `plain` and `detail`
- **AND THEN** the owner's tmux pane shows the available reasoning during managed execution

#### Scenario: Enhanced output is available through the existing display styles

- **WHEN** a headless project instance selects `json` with `detail` or `fancy` with `detail`
- **THEN** the bridge uses the selected style and detail for provider-emitted canonical events

#### Scenario: Relaunch retains the settings selected at birth

- **WHEN** an instance records a launch-time display override and an operator subsequently changes the reusable profile
- **THEN** resuming or relaunching that instance recovers the recorded display settings
- **AND THEN** the next turn uses those settings for live pane output

#### Scenario: An older supported session lacks display metadata

- **WHEN** a supported headless session manifest lacks a display field
- **THEN** resume or relaunch uses the built-in default for that field
