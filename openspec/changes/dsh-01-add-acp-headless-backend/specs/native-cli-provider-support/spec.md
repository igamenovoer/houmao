# Spec Delta

## MODIFIED Requirements

### Requirement: Maintained native CLI provider set excludes Gemini CLI
Houmao SHALL maintain native CLI launch support for Claude Code, Codex, Kimi Code, and DeepSeek Harness (`dsh`). DSH operations SHALL be limited to its explicitly qualified backend capabilities.

The identifiers `gemini`, `gemini_cli`, and `gemini_headless` SHALL NOT be accepted as current provider, tool, compatibility-adapter, or backend values by maintained launch, join, resume, relaunch, gateway, server, passive-server, project, credential, model-selection, or system-skill interfaces.

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
