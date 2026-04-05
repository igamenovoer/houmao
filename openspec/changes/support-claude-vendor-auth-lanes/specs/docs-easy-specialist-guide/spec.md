## ADDED Requirements

### Requirement: Easy-specialist guide distinguishes Claude credentials from the optional state template
The easy-specialist guide at `docs/getting-started/easy-specialists.md` SHALL describe Claude credential-providing methods separately from the optional `--claude-state-template-file` input.

When the guide describes Claude specialist authoring, it SHALL make clear that `claude_state.template.json` is optional runtime bootstrap state and not itself a credential-providing method.

#### Scenario: Reader sees Claude state template documented as optional bootstrap input
- **WHEN** a reader follows the easy-specialist guide for a Claude specialist
- **THEN** the page distinguishes Claude credential inputs from `--claude-state-template-file`
- **AND THEN** it describes the state-template file as optional bootstrap state rather than as Claude credentials
