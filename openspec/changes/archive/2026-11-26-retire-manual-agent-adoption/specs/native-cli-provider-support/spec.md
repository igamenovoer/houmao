# Spec Delta

## MODIFIED Requirements

### Requirement: Maintained native CLI provider set excludes Gemini CLI
Houmao SHALL maintain qualified native CLI launch operations for Claude Code, Codex, Kimi Code, DeepSeek Harness (`dsh`), and Hermes Agent (`hermes`).

The identifiers `gemini`, `gemini_cli`, and `gemini_headless` SHALL NOT be accepted as current provider, tool, compatibility-adapter, or backend values by maintained launch, resume, relaunch, gateway, server, passive-server, project, credential, model-selection, or system-skill interfaces.

#### Scenario: Current provider selection rejects Gemini
- **WHEN** a caller supplies a Gemini tool, provider, or backend identifier to a maintained Houmao interface
- **THEN** the interface rejects the value through its normal unsupported-input validation
- **AND THEN** Houmao does not route the request to a Gemini process

#### Scenario: Remaining provider set stays available
- **WHEN** a caller selects a maintained Claude, Codex, or Kimi workflow
- **THEN** Houmao continues resolving the applicable maintained provider path
- **AND THEN** Gemini removal does not introduce a replacement or alias for those providers

#### Scenario: DSH Is Selected Through Maintained Tool Surfaces
- **WHEN** a caller selects `dsh` with a supported qualified backend through project, credential, model, launch, gateway, or passive-server interfaces
- **THEN** those interfaces resolve the DSH tool consistently
- **AND THEN** an unsupported DSH operation fails explicitly instead of being routed through another tool

#### Scenario: Hermes Is Selected Through Maintained Tool Surfaces

- **WHEN** an operator selects `hermes` with a supported backend through a maintained managed launch path
- **THEN** the path resolves Hermes consistently and identifies the selected run mode
- **AND THEN** an unsupported Hermes operation is rejected without selecting a different tool
