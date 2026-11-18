# houmao-mgr-project-agents-launch-profiles Specification

## ADDED Requirements

### Requirement: Launch-dossier commands manage explicit profile tool parameters

`houmao-mgr internals native-agent launch-dossiers add|set` (and compatibility `project agents launch-profiles add|set`) SHALL accept `--tool-params <json-or-@path>` validated against the referenced recipe's tool schema, `set` SHALL accept `--clear-tool-params`, and `get` SHALL report stored `tool_params` as structured metadata.

#### Scenario: Explicit launch profile add and set manage tool_params
- **WHEN** an operator runs `houmao-mgr internals native-agent launch-dossiers add --name ci --recipe claude-default --tool-params '{"include_partial_messages":true}'`
- **AND WHEN** the operator inspects `ci` with `get --name ci` and clears `tool_params` with `set --name ci --clear-tool-params`
- **THEN** `add` stores and projects `tool_params` in `.houmao/agents/launch-profiles/ci.yaml`, `get` reports it, and `set --clear-tool-params` removes it without dropping unrelated profile fields
