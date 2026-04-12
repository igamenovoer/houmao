## ADDED Requirements

### Requirement: Codex launch preferences use final CLI config overrides
For Houmao-managed Codex launches, the runtime SHALL pass Houmao-owned non-secret preferences as final Codex CLI config override arguments so those preferences take precedence over Codex config layers discovered from the launch working directory.

The runtime SHALL still preserve the same supported non-secret preferences in the generated Codex runtime home config when those preferences already have a runtime-home projection path.

At minimum, the Codex CLI override preference layer SHALL cover:

- resolved launch-owned model name,
- resolved launch-owned reasoning effort,
- unattended approval and sandbox posture when unattended policy owns those values,
- selected model provider when Houmao owns provider selection for the launch,
- non-secret provider contract fields needed to prevent project-local provider config from changing a Houmao-owned provider selection.

The runtime SHALL NOT pass secret values such as API keys, auth JSON, OAuth tokens, cookies, or bearer tokens through CLI arguments.

#### Scenario: Project-local Codex reasoning config cannot override Houmao launch preference
- **WHEN** a Houmao-managed Codex launch resolves reasoning level `2` to `model_reasoning_effort = "low"`
- **AND WHEN** the generated Codex runtime home records `model_reasoning_effort = "low"`
- **AND WHEN** the launch working directory or one of its ancestors contains `.codex/config.toml` with `model_reasoning_effort = "high"`
- **THEN** the final Codex process arguments include a CLI config override for `model_reasoning_effort = "low"`
- **AND THEN** the live Codex session uses the Houmao-resolved reasoning preference

#### Scenario: Generated Codex home config remains as fallback state
- **WHEN** a Houmao-managed Codex launch resolves model `gpt-5.4` and reasoning effort `low`
- **THEN** the generated Codex runtime home config records those non-secret values when their runtime-home projection paths exist
- **AND THEN** the final Codex process arguments also include matching CLI config overrides for those Houmao-owned preferences
- **AND THEN** launches without a conflicting cwd/project Codex config still have readable generated-home fallback state

#### Scenario: Env-only provider selection is pinned without exposing secrets
- **WHEN** a Houmao-managed Codex launch selects an env-only provider configuration owned by the selected setup or launch profile
- **THEN** the final Codex process arguments include CLI config overrides for the non-secret selected provider name and required provider contract fields
- **AND THEN** the provider API key remains supplied through the existing env or auth-file mechanism
- **AND THEN** the API key value is not present in the process argument list

#### Scenario: Generated launch helper keeps explicit passthrough as manual override
- **WHEN** an operator manually invokes a generated Codex `launch.sh` helper with extra trailing Codex CLI config override args
- **THEN** those manually supplied trailing args remain later in the generated helper command than Houmao-generated preferences
- **AND THEN** normal managed launches that do not supply trailing passthrough args still use the Houmao-resolved preference layer
