# Spec Delta

## MODIFIED Requirements

### Requirement: Headless prompt submission reuses the unified model configuration as a request-scoped execution override
For a headless backend that supports request-scoped overrides, the system SHALL accept an optional request-scoped `execution.model` object that reuses the same model-configuration shape as launch-owned model selection.

`execution.model.name` SHALL use the same model-name field as launch-owned model selection.

`execution.model.reasoning.level` SHALL use the same non-negative tool/model-relative preset-index semantics as launch-owned model selection.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

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

#### Scenario: Negative request reasoning is rejected
- **WHEN** a caller submits a headless prompt request with `execution.model.reasoning.level = -1`
- **THEN** the system rejects that request clearly
- **AND THEN** the accepted request-scoped reasoning domain remains non-negative integers only

#### Scenario: Request-scoped zero is rejected when the resolved runtime lacks an off preset
- **WHEN** a managed headless agent resolves to a tool/model ladder without an explicit off preset
- **AND WHEN** the caller submits a headless prompt request with `execution.model.reasoning.level = 0`
- **THEN** the system rejects that request clearly
- **AND THEN** it does not silently reinterpret `0` as the first positive preset

#### Scenario: Hermes Headless Rejects a Per-Turn Override

- **WHEN** a caller supplies `execution.model` to a Hermes headless agent
- **THEN** Houmao rejects the unsupported override before launching a CLI turn
- **AND THEN** the bound session's selected model and provider remain available for ordinary prompts

## ADDED Requirements

### Requirement: Managed Hermes Selects Its Model Route at Launch

Houmao SHALL validate the explicit Hermes model and provider configuration against the selected launch profile and project it into the private Hermes home. Changes to a session-bound route SHALL use a qualified lifecycle operation or a new session.

#### Scenario: A Managed Hermes Model Is Selected

- **WHEN** a launch profile selects a Hermes endpoint, model, and explicit credential source
- **THEN** the launched Hermes session uses that selection
- **AND THEN** launch diagnostics expose the selected model and provider without exposing the credential
