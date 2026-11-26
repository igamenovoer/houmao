# Spec Delta

## ADDED Requirements

### Requirement: Managed Hermes Projects Launch Reasoning Effort

Houmao SHALL resolve an authored Hermes launch reasoning level against the maintained custom Chat Completions ladder. A resolved level SHALL take precedence over the optional exact effort in `tool_params.reasoning_effort`. Houmao SHALL project the selected effort to `agent.reasoning_effort` in the private `HERMES_HOME/config.yaml` before service, TUI, or headless launch and record its source and value in secret-free launch provenance.

#### Scenario: A Numeric Preset Selects a Native Effort

- **WHEN** the effective Hermes reasoning level is `0`, `1`, `2`, `3`, `4`, `5`, or `6`
- **THEN** the private YAML contains `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, or `max`, respectively, at `agent.reasoning_effort`
- **AND THEN** launch provenance identifies the requested and effective levels and the selected native value

#### Scenario: A Higher Preset Saturates at Max

- **WHEN** a managed Hermes launch selects a reasoning level above `6`
- **THEN** the private YAML contains `agent.reasoning_effort: max`
- **AND THEN** launch provenance records the requested level, effective level `6`, and saturation

#### Scenario: The Numeric Level Overrides the Exact Effort Default

- **WHEN** valid Hermes tool parameters supply `reasoning_effort: low` and the effective launch level is `5`
- **THEN** the private YAML contains `agent.reasoning_effort: xhigh`
- **AND THEN** provenance identifies the numeric selection as the source of the effective effort

#### Scenario: An Exact Effort Supplies the Default

- **WHEN** Hermes tool parameters supply `reasoning_effort: xhigh` and the launch resolves no numeric level
- **THEN** the private YAML contains `agent.reasoning_effort: xhigh`
- **AND THEN** provenance identifies the tool parameter as the source of the selected effort

#### Scenario: Omission Defers to Hermes

- **WHEN** the launch supplies neither a numeric level nor an exact Hermes effort
- **THEN** the private YAML omits `agent.reasoning_effort` so Hermes supplies its native default

### Requirement: Managed Hermes Validates Reasoning Inputs Before Home Preparation

Houmao SHALL accept the exact Hermes effort labels `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, and `max`. It SHALL reject invalid launch reasoning inputs before creating or modifying the managed home.

#### Scenario: An Invalid Exact Effort Is Rejected Even With a Numeric Override

- **WHEN** an authored Hermes tool parameter supplies a value outside the allowed labels, such as `ultra` or a boolean
- **THEN** launch validation reports the `reasoning_effort` field and the accepted labels
- **AND THEN** validation rejects the input even if the launch also selects a valid numeric preset

#### Scenario: A Negative Level Is Rejected

- **WHEN** a Hermes launch is requested with a negative reasoning level
- **THEN** launch validation reports that reasoning levels must be non-negative
