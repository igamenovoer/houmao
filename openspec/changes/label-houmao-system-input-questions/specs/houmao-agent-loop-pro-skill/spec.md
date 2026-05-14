## ADDED Requirements

### Requirement: Pro system-input questions distinguish required and optional loop runtime inputs
The packaged `houmao-agent-loop-pro` skill SHALL use required/optional input labels when asking users for Houmao loop system-operation values.

Those labeled questions SHALL apply to loop directory selection, project context roots, generated artifact locations, workspace preparation targets, agent-definition preparation inputs, validation targets, launch targets, operator-control targets, mail-notifier posture, lifecycle mode, and other Houmao runtime mechanics.

The pro skill SHALL NOT impose required/optional labels on user-task intent questions about objectives, acceptance criteria, domain constraints, participant reasoning, or business semantics unless the specific question asks for Houmao runtime behavior.

#### Scenario: Init asks for loop directory as required input
- **WHEN** `houmao-agent-loop-pro init` needs the user to choose an output loop directory
- **THEN** the skill asks with a required section that names the loop directory
- **AND THEN** it includes an optional section for project root, project context hints, naming preferences, or states that no optional input is needed

#### Scenario: Preparation asks for system blockers with optional defaults
- **WHEN** `prepare-agents`, `prepare-workspace`, `validate-loop`, or `launch-agents` lacks a Houmao system input needed to proceed
- **THEN** the skill asks with required inputs separated from optional modifiers
- **AND THEN** the optional section identifies defaults, skip behavior, or manual alternatives when they exist

#### Scenario: Intent clarification remains domain-focused
- **WHEN** `clarify-intent` asks about objective ambiguity, acceptance semantics, participant responsibilities, or task-specific loop behavior
- **THEN** the question is not required to use required/optional system-input labels
- **AND THEN** the clarification flow still uses required/optional labels if it asks for a Houmao runtime setting such as topology mode, workspace sharing, mail-notifier mode, or lifecycle control behavior
