# Spec Delta

## MODIFIED Requirements

### Requirement: Houmao agent definition provides a ready project-profile workflow
The system SHALL provide a `houmao-agent-definition` subskill exposed as `create-agent-fast-forward` for preparing a launchable specialist-backed project profile from one operator request.

That workflow SHALL create or select a specialist, create or update an project profile backed by that specialist, store supplied launch defaults on the profile, and report the resulting launch command without launching the managed agent.

The workflow SHALL prefer unattended prompt mode by default unless the user explicitly requests another prompt mode.

When the operator omits the run mode, the workflow SHALL defer to the selected tool's project default, including `web` for DSH.

The workflow SHALL store a requested supported mode through the profile authoring surface and include a one-shot `--mode` override only when one is requested.

The workflow MAY mention older ready-profile wording only as compatibility terminology; `create-agent-fast-forward` SHALL be the primary skill subcommand name.

#### Scenario: Fast-forward profile preparation does not launch
- **WHEN** a user asks to run `create-agent-fast-forward` for a specialist-backed agent profile
- **THEN** the unified skill routes to the fast-forward workflow under `houmao-agent-definition`
- **AND THEN** the workflow creates or selects the specialist, creates or updates the project profile, and prints the launch command
- **AND THEN** it does not launch a live managed agent

#### Scenario: Fast-forward profile preparation defaults prompt mode separately from launch posture
- **WHEN** a user asks to run `create-agent-fast-forward` for a TUI-capable specialist-backed agent profile
- **AND WHEN** the user does not request headless execution
- **THEN** the workflow may store unattended prompt mode as the default prompt mode
- **AND THEN** it omits the profile mode and prints a launch command that uses the tool's default

#### Scenario: Operator selects a reusable service profile

- **WHEN** the operator requests persistent service mode for a specialist that supports it
- **THEN** the workflow records the requested `service` mode and reports the launch command without starting the agent
