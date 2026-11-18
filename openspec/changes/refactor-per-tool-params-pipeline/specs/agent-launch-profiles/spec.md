# agent-launch-profiles Specification

## ADDED Requirements

### Requirement: Launch profiles store per-tool parameters as birth-time configuration

The shared launch-profile object family SHALL support optional secret-free `tool_params` validated against the referenced specialist or recipe tool's partial schema, persisted in the project catalog, and projected to `.houmao/agents/launch-profiles/<name>.yaml`. Patch mutation SHALL merge `tool_params` field-by-field unless explicit clear or replacement is requested, replacement mutation SHALL clear omitted `tool_params`, and stored mutations SHALL not alter live instances.

#### Scenario: Profile stores and projects validated per-tool parameters
- **WHEN** an operator creates project profile `alice` targeting a DSH specialist with valid DSH `tool_params`
- **THEN** the catalog stores `tool_params` on `alice` and projects it into `.houmao/agents/launch-profiles/alice.yaml`
- **AND THEN** `profile` or `launch-profile` inspection reports `tool_params` without inline secrets

#### Scenario: Profile rejects tool_params belonging to another tool
- **WHEN** an operator creates or updates a launch profile targeting a `codex` source while supplying `claude`-only `tool_params` keys
- **THEN** validation fails clearly before persisting the profile mutation

#### Scenario: Patch merges profile tool_params while replacement clears omitted tool_params
- **WHEN** launch profile `alice` stores `tool_params` with multiple nested settings
- **AND WHEN** an operator patches `alice` with a partial `tool_params` update or replaces `alice` without `tool_params`
- **THEN** patch mutation preserves unspecified nested `tool_params` keys on `alice`
- **AND THEN** same-lane replacement without `tool_params` clears the profile's stored `tool_params`
