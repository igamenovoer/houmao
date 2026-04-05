## ADDED Requirements

### Requirement: `houmao-create-specialist` describes Claude credential lanes separately from optional state templates
The packaged `houmao-create-specialist` skill SHALL describe Claude credential-providing methods separately from optional Claude runtime-state template inputs.

When the skill lists Claude-specific create inputs or discovery outcomes, it SHALL treat:

- supported Claude credential or login-state lanes as Claude auth methods,
- `claude_state.template.json` only as optional reusable bootstrap state for runtime preparation.

The skill SHALL NOT present `claude_state.template.json` as one of the ways to provide Claude credentials.

#### Scenario: Installed skill does not present the Claude state template as credentials
- **WHEN** an agent reads the installed `houmao-create-specialist` skill
- **THEN** the skill distinguishes Claude credential-providing methods from the optional Claude state-template input
- **AND THEN** it does not describe `claude_state.template.json` as a Claude credential lane
