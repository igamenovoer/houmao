## MODIFIED Requirements

### Requirement: Houmao agent definition provides a ready easy-profile workflow
The system SHALL provide a `houmao-agent-definition` subskill exposed as `create-agent-fast-forward` for preparing a launchable specialist-backed easy profile from one operator request.

That workflow SHALL create or select a specialist, create or update an easy profile backed by that specialist, store supplied launch defaults on the profile, and report the resulting launch command without launching the managed agent.

The workflow SHALL prefer unattended prompt mode by default unless the user explicitly requests another prompt mode.

The workflow SHALL prefer TUI/local-interactive launch posture when the selected tool supports it and the user does not request headless execution.

The workflow SHALL NOT persist `--headless` on the easy profile or include `--headless` in the reported launch command unless the user explicitly requests headless execution or the selected tool/lane requires headless.

The workflow MAY mention older ready-profile wording only as compatibility terminology; `create-agent-fast-forward` SHALL be the primary skill subcommand name.

#### Scenario: Fast-forward profile preparation does not launch
- **WHEN** a user asks to run `create-agent-fast-forward` for a specialist-backed agent profile
- **THEN** the unified skill routes to the fast-forward workflow under `houmao-agent-definition`
- **AND THEN** the workflow creates or selects the specialist, creates or updates the easy profile, and prints the launch command
- **AND THEN** it does not launch a live managed agent

#### Scenario: Fast-forward profile preparation defaults prompt mode separately from launch posture
- **WHEN** a user asks to run `create-agent-fast-forward` for a TUI-capable specialist-backed agent profile
- **AND WHEN** the user does not request headless execution
- **THEN** the workflow may store unattended prompt mode as the default prompt mode
- **AND THEN** it omits profile `--headless` and prints a launch command without `--headless`
