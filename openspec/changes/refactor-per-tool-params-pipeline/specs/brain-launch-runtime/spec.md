# brain-launch-runtime Specification

## MODIFIED Requirements

### Requirement: DSH Runtime Configuration Is Explicit and Isolated

Managed DSH launches SHALL isolate the Harness home, shared-agent root, profile, persistence, and selected skill roots from resolved `DshToolParams` (`tool_params` layers materialized to `<DSH_HOME>/houmao-tool-params.yaml` and `<DSH_HOME>/houmao-profile.patch.json`) rather than requiring a standalone `dsh-setup.yaml` file. Provider route, endpoint protocol, credential reference, Houmao `model.name` selection, and required model metadata SHALL resolve explicitly, native DeepSeek Messages and generic compatible routes SHALL remain distinct configurations, and secrets SHALL stay outside persisted public launch metadata.

#### Scenario: Two Agents Use Different Model Routes
- **WHEN** two DSH agents use different credentials, models, skill sets, `tool_params`, or endpoints in the same workspace
- **THEN** each agent uses its selected managed configuration without inheriting the other's home, history, or user-global credentials

#### Scenario: A Chat Endpoint Is Supplied to a Messages Route
- **WHEN** a selected DSH route requires Messages but the supplied `tool_params` endpoint configuration declares only Chat Completions
- **THEN** validation rejects the combination before agent work
- **AND THEN** Houmao does not relabel the protocol or silently choose another model adapter

#### Scenario: The Provider Route Is Missing
- **WHEN** merged DSH `tool_params` has no valid provider route or lacks required model metadata
- **THEN** launch fails with an actionable missing-input diagnostic instead of using a shipped model or capacity default

#### Scenario: Standalone dsh-setup.yaml and Duplicate selected_model Are Retired
- **WHEN** a setup or preset attempts to configure DSH via legacy `dsh-setup.yaml` or `selected_model` inside `tool_params`
- **THEN** validation rejects the legacy input and directs the caller to `tool_params` (`tool-params.yaml` or profile/specialist `tool_params`) and Houmao's unified `model.name` field
