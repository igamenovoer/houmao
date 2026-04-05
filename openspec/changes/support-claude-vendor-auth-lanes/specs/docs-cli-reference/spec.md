## ADDED Requirements

### Requirement: CLI reference distinguishes Claude credential inputs from the optional state template
The `houmao-mgr` CLI reference SHALL describe Claude credential-providing inputs separately from the optional Claude state-template input on both:

- `project agents tools claude auth ...`
- `project easy specialist create --tool claude`

When the reference documents Claude-specific flags, it SHALL make clear that `claude_state.template.json` or `--claude-state-template-file` is optional runtime bootstrap state and not itself a credential-providing method.

#### Scenario: Reader sees the Claude state template documented separately in the CLI reference
- **WHEN** a reader looks up the Claude project-auth or easy-specialist options in `docs/reference/cli/houmao-mgr.md`
- **THEN** the page distinguishes credential-providing Claude inputs from the optional state-template input
- **AND THEN** it does not present the state-template input as one of the ways to authenticate Claude
