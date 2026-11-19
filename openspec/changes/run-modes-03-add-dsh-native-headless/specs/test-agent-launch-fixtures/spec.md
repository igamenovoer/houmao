# Spec Delta

## MODIFIED Requirements

### Requirement: DSH Headless Fixtures Reuse Generic Local Configuration

The fixture helper SHALL prepare raw and managed one-shot DSH headless CLI launches for `self-hosted` and `cloud-api` using resolved `tool_params`, explicit model and compatibility metadata, and private isolated homes. Cloud preparation SHALL use local key and endpoint references without auth JSON. Explicit endpoint-only `pi-ai/openai-completions` fixtures SHALL use the native authorization placeholder. Unsupported DSH modes and native login SHALL fail explicitly before authenticated run state is created.

#### Scenario: Fresh Host Uses DeepSeek Without a Local Model
- **WHEN** a developer provides the cloud key, the selected Messages-compatible endpoint, and an explicit model through the local fixture configuration
- **THEN** a native DSH headless test agent can be prepared without a deployed self-hosted model or saved vendor-login files

#### Scenario: Generic Self-Hosted Route Has No Explicit Capabilities
- **WHEN** a self-hosted DSH route lacks model capacity or `reasoning_efforts` metadata required by its selected adapter
- **THEN** preparation fails with those missing inputs named instead of borrowing another model's defaults

#### Scenario: CI Has No Local Provider Account
- **WHEN** hermetic DSH fixture tests execute without local credentials
- **THEN** synthetic endpoints and subprocesses validate preparation and lifecycle without paid requests or personal auth discovery

#### Scenario: Self-Hosted Fixture Can Complete an Endpoint-Only Prompt
- **WHEN** a developer prepares a self-hosted `pi-ai/openai-completions` fixture with explicit `reasoning_efforts`, `compat` overrides, and an endpoint that accepts the placeholder authorization header
- **THEN** fixture preparation emits `tool_params` with `api_key_env: null`, the configured `compat` mapping, and `reasoning_efforts`
- **AND THEN** the launched fixture completes a prompt with the native placeholder and without an operator-supplied API key

#### Scenario: Managed and raw fixtures select the same native profile

- **WHEN** a developer qualifies the raw and managed headless fixtures with matching inputs
- **THEN** both exercise `--profile headless --json` and exact native continuation through a new worker per prompt
