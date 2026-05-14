## ADDED Requirements

### Requirement: Repo-owned Codex setup bundles avoid fixed model defaults
Repo-owned Codex setup bundles SHALL NOT set a fixed Codex model name solely to provide a default model.

Repo-owned Codex setup bundles MAY set provider routing, reasoning-effort defaults, personality, and non-model TUI startup configuration.

Provider-specific setup bundles MAY document how an operator can explicitly select a model when the selected OpenAI-compatible provider requires one, but committed repo-owned defaults SHALL remain free of stale model pins.

#### Scenario: Default Codex setup carries no model pin
- **WHEN** a developer inspects the repo-owned default Codex setup bundle
- **THEN** the setup config does not contain a `model` key
- **AND THEN** the setup may still contain `model_reasoning_effort` and non-model Codex preferences

#### Scenario: Yunwu Codex setup keeps provider routing without model pin
- **WHEN** a developer inspects the repo-owned `yunwu-openai` Codex setup bundle
- **THEN** the setup config selects `model_provider = "yunwu-openai"`
- **AND THEN** the `yunwu-openai` provider block remains configured for the OpenAI-compatible endpoint
- **AND THEN** the setup config does not contain a fixed `model` key

#### Scenario: Explicit provider model remains an operator choice
- **WHEN** a developer needs a specific model for a provider-specific Codex launch
- **THEN** they can provide that model through launch-owned model configuration or copied native Codex config
- **AND THEN** the repo-owned setup bundle does not need to embed that model as its default
