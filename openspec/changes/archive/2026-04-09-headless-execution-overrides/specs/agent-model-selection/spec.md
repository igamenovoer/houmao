## ADDED Requirements

### Requirement: Headless prompt submission reuses the unified model configuration as a request-scoped execution override
For supported headless prompt submission surfaces, the system SHALL accept an optional request-scoped `execution.model` object that reuses the same normalized model-configuration shape as launch-owned model selection.

`execution.model.name` SHALL use the same normalized model-name field as launch-owned model selection.

`execution.model.reasoning.level` SHALL use the same normalized integer range `1..10`.

When a request supplies only one of `name` or `reasoning`, omitted subfields SHALL inherit from the addressed agent's launch-resolved effective model configuration for that prompt.

The request-scoped override SHALL apply only to the accepted headless prompt submission being executed.

The request-scoped override SHALL NOT rewrite copied baseline state, recipe state, specialist state, launch-profile state, runtime manifests, or later default execution state.

#### Scenario: Model-only request override inherits the launch-resolved reasoning level
- **WHEN** a managed headless agent has launch-resolved model `gpt-5.4` with reasoning level `6`
- **AND WHEN** the caller submits a headless prompt request with `execution.model.name = "gpt-5.4-mini"` and no request reasoning override
- **THEN** the effective model for that accepted prompt is `gpt-5.4-mini`
- **AND THEN** the effective reasoning level for that accepted prompt remains `6`

#### Scenario: Reasoning-only request override inherits the launch-resolved model name
- **WHEN** a managed headless agent has launch-resolved model `gpt-5.4` with reasoning level `6`
- **AND WHEN** the caller submits a headless prompt request with `execution.model.reasoning.level = 3` and no request model-name override
- **THEN** the effective model for that accepted prompt remains `gpt-5.4`
- **AND THEN** the effective reasoning level for that accepted prompt is `3`

#### Scenario: Request-scoped override does not become the next prompt default
- **WHEN** a managed headless agent has launch-resolved model `gpt-5.4`
- **AND WHEN** one accepted prompt runs with request override `execution.model.name = "gpt-5.4-mini"`
- **AND WHEN** a later accepted prompt omits `execution.model`
- **THEN** the later prompt uses the agent's normal launch-resolved default model
- **AND THEN** the earlier request override does not remain as live execution state

#### Scenario: Out-of-range request reasoning is rejected
- **WHEN** a caller submits a headless prompt request with `execution.model.reasoning.level = 11`
- **THEN** the system rejects that request clearly
- **AND THEN** the accepted normalized request-scoped reasoning range remains exactly `1..10`
