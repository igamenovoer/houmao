## MODIFIED Requirements

### Requirement: Build and launch resolution applies launch-profile defaults between recipe defaults and direct overrides
When a launch is started from a reusable launch profile, the build and runtime pipeline SHALL resolve effective launch inputs by applying launch-profile defaults after source recipe defaults and before direct launch-time overrides.

At minimum, the pipeline SHALL allow launch-profile-derived values to influence:
- effective auth selection
- effective model selection
- effective normalized reasoning level
- operator prompt-mode intent
- durable non-secret env records
- declarative mailbox configuration
- managed-agent identity defaults
- launch provenance

The resulting build manifest or runtime launch metadata SHALL preserve profile provenance in a secret-free form sufficient for inspection and replay, including whether the birth-time config came from an easy profile or an explicit launch profile.

#### Scenario: Launch-profile-derived auth and mailbox defaults survive into build and runtime resolution
- **WHEN** a launch profile stores auth override `alice-creds` and declarative mailbox defaults
- **AND WHEN** a managed-agent launch is started from that profile without conflicting direct overrides
- **THEN** brain construction uses `alice-creds` as the effective auth selection
- **AND THEN** the resulting launch pipeline carries the profile-derived mailbox configuration into runtime launch resolution

#### Scenario: Direct launch override still wins over launch-profile-owned workdir
- **WHEN** a launch profile stores working directory `/repos/alice`
- **AND WHEN** the operator launches from that profile with direct workdir override `/tmp/debug`
- **THEN** runtime launch uses `/tmp/debug` as the effective working directory
- **AND THEN** profile provenance still records that the launch originated from the named profile

#### Scenario: Direct launch override wins over launch-profile-owned model
- **WHEN** a launch profile stores model override `gpt-5.4-mini`
- **AND WHEN** the operator launches from that profile with direct override `--model gpt-5.4-nano`
- **THEN** brain construction uses `gpt-5.4-nano` as the effective model
- **AND THEN** profile provenance still records that the launch originated from the named profile

#### Scenario: Direct launch reasoning override wins over launch-profile-owned reasoning
- **WHEN** a launch profile stores reasoning override `4`
- **AND WHEN** the operator launches from that profile with direct override `--reasoning-level 8`
- **THEN** brain construction uses normalized reasoning level `8` as the effective launch-owned value
- **AND THEN** profile provenance still records that the launch originated from the named profile

## ADDED Requirements

### Requirement: Brain construction projects resolved model configuration into runtime homes and manifests
During brain-home construction, the system SHALL resolve the effective model configuration before provider startup and SHALL project that configuration into the constructed runtime home or launch environment through maintained tool-native surfaces and a Houmao-owned reasoning mapping policy.

At minimum, the maintained direct model-name projection surfaces SHALL include:
- Claude launch env `ANTHROPIC_MODEL`
- Codex runtime `${CODEX_HOME}/config.toml` key `model`
- Gemini runtime `${GEMINI_CLI_HOME}/.gemini/settings.json` key path `model.name`

This projection SHALL happen after setup copy and auth projection, and before launch helper synthesis and provider-start policy mutation.

For reasoning-level projection, the system SHALL consult a dedicated Houmao mapping-policy module that can consider:
- normalized requested level
- selected tool
- selected model name
- tool version when available
- runtime config context when required

The built manifest SHALL preserve secret-free model-selection provenance sufficient to inspect:
- the resolved effective model,
- the requested normalized reasoning level,
- the resolved native reasoning mapping summary,
- whether launch-profile or direct launch input contributed it,
- the tool-native projection target family used for that build.

#### Scenario: Built manifest records the resolved effective model configuration
- **WHEN** a recipe default, launch-profile override, and direct launch override are available for one build
- **AND WHEN** the direct launch override wins
- **THEN** the built manifest records the direct value as the resolved effective model
- **AND THEN** the manifest records secret-free provenance that the value came from direct launch input

#### Scenario: Built manifest records requested normalized reasoning and resolved native mapping
- **WHEN** one build resolves launch-owned reasoning level `7`
- **AND WHEN** the mapping policy projects that request into one native tool-specific reasoning configuration
- **THEN** the built manifest records requested normalized level `7`
- **AND THEN** the manifest records a secret-free summary of the resolved native mapping used for that runtime

#### Scenario: Explicit Codex model survives later launch-policy mutation
- **WHEN** a Codex runtime build resolves model `gpt-5.4-mini`
- **AND WHEN** unattended launch policy later patches approval, sandbox, trust, and migration-owned config state
- **THEN** the runtime `config.toml` still records `model = "gpt-5.4-mini"`
- **AND THEN** the launch-policy path does not replace that explicit resolved model with a migration fallback value

#### Scenario: Explicit reasoning projection survives later launch-policy mutation
- **WHEN** one runtime build resolves launch-owned reasoning level `9`
- **AND WHEN** the mapping policy projects that request into native reasoning settings before unattended launch-policy mutation
- **THEN** later unattended launch-policy mutation does not silently discard that explicit reasoning projection
- **AND THEN** any clamp or native rewrite applied by Houmao remains visible in manifest provenance
