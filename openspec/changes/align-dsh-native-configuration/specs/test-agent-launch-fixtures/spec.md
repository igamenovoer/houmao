# test-agent-launch-fixtures Specification

## MODIFIED Requirements

### Requirement: DSH Headless Fixtures Reuse Generic Local Configuration

The fixture helper SHALL prepare raw and managed DSH ACP launches from `self-hosted` and `cloud-api` cases using resolved `DshToolParams` (`tool_params`), explicit model and compatibility metadata, and isolated private homes. Cloud preparation SHALL use local key and endpoint references without auth JSON. An explicitly selected endpoint-only `pi-ai/openai-completions` fixture SHALL use the supported native placeholder projection for the selected endpoint. Unimplemented DSH mode or native-login selections SHALL fail explicitly before creating authenticated run state.

#### Scenario: Fresh Host Uses DeepSeek Without a Local Model
- **WHEN** a developer provides the cloud key, the selected Messages-compatible endpoint, and an explicit model through the local fixture configuration
- **THEN** a DSH ACP test agent can be prepared without a deployed self-hosted model or saved vendor-login files

#### Scenario: Generic Self-Hosted Route Has No Explicit Capabilities
- **WHEN** a self-hosted DSH route lacks model capacity or `reasoning_efforts` metadata required by its selected adapter
- **THEN** preparation fails with those missing inputs named instead of borrowing another model's defaults

#### Scenario: Self-Hosted Fixture Can Complete an Endpoint-Only Prompt
- **WHEN** a developer prepares a self-hosted `pi-ai/openai-completions` fixture with explicit `reasoning_efforts`, `compat` overrides, and an endpoint that accepts the placeholder authorization header
- **THEN** fixture preparation emits `tool_params` with `api_key_env: null`, the configured `compat` mapping, and `reasoning_efforts`
- **AND THEN** the launched fixture completes a prompt with the native placeholder and without an operator-supplied API key

#### Scenario: CI Has No Local Provider Account
- **WHEN** hermetic DSH fixture tests execute without local credentials
- **THEN** synthetic endpoints and subprocesses validate preparation and lifecycle without paid requests or personal auth discovery

### Requirement: DSH Web Fixtures Share the Existing Generic Endpoint Cases

DSH `tui` fixture preparation SHALL reuse the `self-hosted` and `cloud-api` cases, `DshToolParams` compatibility and reasoning inputs, and private credential/run roots established for headless DSH. Raw and managed preparation SHALL expose the same native Web behavior. Browser startup and connection credentials SHALL remain controlled locally without entering tracked reports.

#### Scenario: A Fresh Host Uses Cloud DSH Interactively
- **WHEN** a developer configures only the selected DeepSeek key, endpoint, and model
- **THEN** a DSH Web test agent can be prepared without a self-hosted model, auth JSON, or desktop display

#### Scenario: Self-Hosted Web Fixture Shares Tool-Params Compatibility Inputs
- **WHEN** a developer prepares a `mode=tui` self-hosted `pi-ai/openai-completions` DSH fixture with explicit `compat` and `reasoning_efforts` settings
- **THEN** raw and managed Web preparations emit the same DSH `tool_params` compatibility, reasoning, and endpoint-only contract as headless DSH

#### Scenario: A Browser Connects to the Managed Fixture
- **WHEN** a qualification browser signs in through the fixture's private local connection mechanism
- **THEN** it opens the same native session targeted by the programmatic adapter
- **AND THEN** public fixture summaries contain only non-secret location and identity metadata
