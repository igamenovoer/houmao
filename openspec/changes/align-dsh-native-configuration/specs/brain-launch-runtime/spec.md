# brain-launch-runtime Specification

## MODIFIED Requirements

### Requirement: DSH Runtime Configuration Is Explicit and Isolated

Managed DSH launches SHALL isolate the Harness home, shared-agent root, profile, persistence, and selected skill roots from resolved `DshToolParams` (`tool_params` layers materialized to `<DSH_HOME>/houmao-tool-params.yaml` and `<DSH_HOME>/houmao-profile.patch.json`). Provider adapter, wire protocol, credential roles, Houmao `model.name` selection, model catalog, and compatibility metadata SHALL resolve explicitly. The model catalog SHALL use `reasoning_efforts`, and secrets SHALL stay outside persisted public launch metadata.

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

#### Scenario: Legacy Per-Index Reasoning Table Is Rejected
- **WHEN** a DSH `tool_params` layer declares legacy per-index `models[].reasoning` mappings instead of `reasoning_efforts`
- **THEN** validation fails before provider launch with a clear `DshToolParams` schema diagnostic
- **AND THEN** Houmao does not silently rewrite or guess native thinking-slot or compatibility settings

## ADDED Requirements

### Requirement: DSH Compatible Route Projections Preserve Native Adapter Capabilities

Managed DSH compatible-adapter `tool_params` SHALL validate and project supported wire protocols, route-level and model-level compatibility overrides, input modalities, retry policy, and role-bound environment variable names into the isolated DSH profile. Explicit `api_key_env: null` SHALL select endpoint-only configuration for self-hosted `pi-ai/openai-completions` routes. Other routes SHALL require a non-empty API-key reference and value.

#### Scenario: Model Compatibility Overrides Project Without Developer Role Failure
- **WHEN** DSH `tool_params` for a `pi-ai` route declares route or model `compat` fields such as `supports_developer_role: false` and `thinking_format: "qwen"`
- **THEN** the generated isolated DSH profile patch preserves those compatibility fields in native camelCase form for the selected route and model
- **AND THEN** Houmao does not strip compatibility settings down to capacity-only model fields

#### Scenario: Endpoint-Only OpenAI-Compatible Launch Completes a Prompt
- **WHEN** the operator selects a self-hosted `pi-ai/openai-completions` route with `api_key_env: null`, a bundle with only an endpoint value, and an endpoint that accepts the placeholder authorization header
- **THEN** Houmao projects native `apiKeyEnv` to a launcher-owned environment name, supplies a fixed public placeholder to the native process, and completes a prompt through that endpoint
- **AND THEN** credential storage and persisted public configuration contain no placeholder value

#### Scenario: Unsupported Endpoint-Only Route Fails Before Launch
- **WHEN** `tool_params` declares `api_key_env: null` for an adapter and protocol pair other than `pi-ai/openai-completions`
- **THEN** preflight rejects the configuration before runtime mutation

#### Scenario: Custom Credential Environment Names Project Into Isolated Runtime
- **WHEN** DSH `tool_params` declares custom names for `base_url_env` and `api_key_env` that match the selected bundle's endpoint and API-key roles
- **THEN** launch preparation supplies those values from the selected bundle to the isolated DSH process

#### Scenario: Credential Role Mismatch or Environment Collision Fails Preflight
- **WHEN** a declared credential name disagrees with the selected bundle's stored role, a required role value is missing, or a persistent or one-shot launch environment override targets a bound credential name
- **THEN** preflight identifies the field or name and rejects the launch before runtime mutation
- **AND THEN** the error includes no credential values

#### Scenario: Unsupported Compatibility Field Fails Validation Before Launch
- **WHEN** DSH `tool_params` declares an unknown `compat` key, an unsupported protocol for the chosen adapter, or `compat` on a `deepseek` Messages route
- **THEN** validation fails before provider startup and names the offending field

### Requirement: Unattended DSH Launch Composes Coherent Permission Presets

When a managed DSH headless or Web launch applies unattended operator policy, profile generation SHALL register a matching unattended preset in the native permission-presets service and select it as the default preset alongside matching approval and sandbox-policy defaults so native permission-service activation succeeds without preset-mismatch errors. Launches in `as_is` operator mode SHALL omit unattended permission, approval, and sandbox-policy overrides.

#### Scenario: Unattended Launch Activates Native Permission Service Cleanly
- **WHEN** a managed DSH ACP or Web agent starts in `unattended` operator mode
- **THEN** the generated profile patch configures a named unattended permission preset alongside DSH's standard presets, sets it as `defaultPreset`, and aligns `approval` and `sandbox-policy` with that preset
- **AND THEN** DSH starts without a `permission` plugin preset-mismatch activation error in stderr

#### Scenario: As-Is Launch Preserves Native Permission Defaults
- **WHEN** a managed DSH Web agent starts in `as_is` operator mode
- **THEN** the generated profile patch omits unattended `permission`, `approval`, and `sandbox-policy` overrides so native interactive approval behavior remains active
