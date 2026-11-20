# CLI Reference Delta

## ADDED Requirements

### Requirement: The manager reference documents headless launch display configuration

The manager reference SHALL document the display flags and supported values for project launch and specialist-backed profile creation and editing. It SHALL explain independent clears and precedence, headless mode validation, the persisted instance settings, and how display detail presents provider-emitted information.

#### Scenario: An operator configures display for future launches and one instance

- **WHEN** an operator looks up the headless display options in the manager reference
- **THEN** the reference shows a saved project-profile example, a one-shot launch override, and a single-field clear
- **AND THEN** it explains the `plain` and `concise` defaults, the applicable mode, and the use of recorded settings on relaunch

#### Scenario: An operator distinguishes live pane and command output

- **WHEN** an operator wants detailed live headless output or wants to inspect a recorded turn
- **THEN** the reference explains the pane setting, the manager root print style, and the scoped `turn events --detail` option
- **AND THEN** it explains that reasoning visibility depends on the events the provider emits and the selected rendering style and detail
