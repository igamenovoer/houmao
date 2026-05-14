# houmao-agent-ready-profile-workflow Specification

## Purpose
TBD - created by archiving change unify-agent-definition-skills. Update Purpose after archive.
## Requirements
### Requirement: Houmao agent definition provides a ready easy-profile workflow
The system SHALL provide a `houmao-agent-definition` subskill exposed as `create-agent-fast-forward` for preparing a launchable specialist-backed easy profile from one operator request.

That workflow SHALL create or select a specialist, create or update an easy profile backed by that specialist, store supplied launch defaults on the profile, and report the resulting launch command without launching the managed agent.

The workflow SHALL prefer unattended launch posture by default unless the user explicitly requests another prompt mode.

The workflow MAY mention older ready-profile wording only as compatibility terminology; `create-agent-fast-forward` SHALL be the primary skill subcommand name.

#### Scenario: Fast-forward profile preparation does not launch
- **WHEN** a user asks to run `create-agent-fast-forward` for a specialist-backed agent profile
- **THEN** the unified skill routes to the fast-forward workflow under `houmao-agent-definition`
- **AND THEN** the workflow creates or selects the specialist, creates or updates the easy profile, and prints the launch command
- **AND THEN** it does not launch a live managed agent

### Requirement: Ready-profile workflow stores launch defaults instead of manual runtime setup
The `create-agent-fast-forward` workflow SHALL store supported easy-profile defaults for agent identity, workdir, prompt mode, model, reasoning level, environment, mailbox posture, gateway posture, gateway mail-notifier appendix, prompt overlay, and memo seed when those inputs are supplied or selected by the operator.

The workflow SHALL NOT instruct agents to preregister same-root ordinary per-agent mailbox addresses when the later easy-profile launch can own launch-time filesystem mailbox bootstrap for the managed-agent identity.

#### Scenario: Mailbox and gateway defaults are recorded on the profile
- **WHEN** the user asks `create-agent-fast-forward` to prepare an agent profile with mailbox and gateway defaults
- **THEN** the workflow maps those defaults to supported `project easy profile create|set` fields
- **AND THEN** it does not route the user through separate manual mailbox and gateway setup steps for the ordinary default case

### Requirement: Ready-profile workflow reports durable identity facts
After creating or updating the fast-forward easy profile, the workflow SHALL report the specialist name, easy profile name, intended managed-agent identity, stored default posture, and exact launch command.

If a required specialist, profile, tool, credential, or launch-default input is missing after checking the current prompt and recent explicit context, the workflow SHALL ask the user for exactly the missing inputs instead of guessing.

#### Scenario: Fast-forward report includes launch command
- **WHEN** the `create-agent-fast-forward` workflow completes successfully
- **THEN** it reports the specialist and easy-profile names
- **AND THEN** it includes a launch command such as `houmao-mgr project easy instance launch --profile <profile>`
- **AND THEN** it reports any profile defaults that affect later launch identity or runtime posture
