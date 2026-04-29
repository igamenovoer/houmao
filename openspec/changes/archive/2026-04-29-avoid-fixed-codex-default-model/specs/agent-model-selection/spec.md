## ADDED Requirements

### Requirement: Codex unspecified model defaults remain provider-owned
When the resolved Codex model name is absent after applying copied native baseline, source launch defaults, launch-profile defaults, and direct launch overrides, the system SHALL preserve that absence through runtime-home projection and final provider launch arguments.

Houmao SHALL NOT synthesize a fixed Codex model name solely because a Codex runtime config omits `model`.

Houmao MAY still project Codex reasoning configuration when the resolved launch-owned model name is absent, using the maintained fallback reasoning ladder and recording provenance that the model name was provider-owned.

#### Scenario: New Codex launch omits model when no layer selects one
- **WHEN** a Codex runtime is built from repo-owned setup and auth inputs that do not select a model
- **AND WHEN** no source launch config, launch profile, or direct launch override supplies a model
- **THEN** the constructed Codex runtime config does not gain a Houmao-selected `model` key
- **AND THEN** the final Codex launch arguments do not include a Houmao-selected `model` override
- **AND THEN** Codex is allowed to use its provider or catalog default model

#### Scenario: Explicit Codex model override is still projected
- **WHEN** a Codex runtime has no setup-owned default model
- **AND WHEN** a launch profile or direct launch override selects model `gpt-5.4-mini`
- **THEN** Houmao projects `model = "gpt-5.4-mini"` into the constructed Codex runtime config
- **AND THEN** the final Codex launch includes the matching non-secret CLI config override

#### Scenario: Reasoning-only Codex launch does not force a model
- **WHEN** a Codex runtime has no resolved launch-owned model name
- **AND WHEN** the resolved launch-owned reasoning level maps to native `model_reasoning_effort = "medium"`
- **THEN** Houmao projects the native reasoning setting
- **AND THEN** Houmao does not also synthesize a fixed `model` key
- **AND THEN** launch provenance records that reasoning was Houmao-selected while model selection remained provider-owned

### Requirement: Managed Codex startup prompt suppression is independent from model selection
Houmao-managed Codex launches SHALL avoid using a fixed model name as the mechanism for suppressing startup UI prompts.

When Houmao needs to suppress non-essential Codex startup notices or tooltips for managed or automated launches, it SHALL use non-model Codex configuration surfaces.

#### Scenario: Startup tooltip suppression does not select a model
- **WHEN** Houmao configures a managed Codex launch to suppress startup tooltips or availability notices
- **AND WHEN** no launch-owned model name is resolved
- **THEN** the generated Codex config or CLI overrides include only non-model prompt-suppression settings
- **AND THEN** model selection remains provider-owned
