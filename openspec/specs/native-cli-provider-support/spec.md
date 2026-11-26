# native-cli-provider-support Specification

## Purpose
Define Claude Code, Codex, Kimi Code, and qualified DeepSeek Harness operations as Houmao's maintained native CLI support. Apply that provider set to runtime launch, release contents, fixtures, and guidance.
## Requirements
### Requirement: Maintained native CLI provider set excludes Gemini CLI
Houmao SHALL maintain qualified native CLI launch operations for Claude Code, Codex, Kimi Code, DeepSeek Harness (`dsh`), and Hermes Agent (`hermes`).

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

#### Scenario: Hermes Is Selected Through Maintained Tool Surfaces

- **WHEN** an operator selects `hermes` with a supported backend through a maintained managed launch path
- **THEN** the path resolves Hermes consistently and identifies the selected run mode
- **AND THEN** an unsupported Hermes operation is rejected without selecting a different tool

### Requirement: Release contains no Gemini compatibility machinery
Houmao SHALL contain no parser, adapter, alias, tombstone, migration, cleanup routine, or special error path whose purpose is to handle Gemini state from an older release.

#### Scenario: Maintainer inspects current provider code
- **WHEN** a maintainer audits current provider code and schemas after removal
- **THEN** no branch recognizes a Gemini identifier for compatibility, migration, cleanup, or tailored rejection
- **AND THEN** older Gemini state remains entirely outside the current release contract

### Requirement: Maintained assets and guidance do not expose Gemini support
Current runtime assets, tracked fixtures, demos, documentation, schemas, tests, and packaged system skills SHALL NOT advertise, configure, launch, or qualify Gemini CLI as a Houmao provider.

Archived OpenSpec changes and immutable historical logs MAY retain factual Gemini references. Provider-neutral safety guidance MAY mention `.gemini` only as third-party local state that must not be copied or linked by default.

#### Scenario: Maintained-content audit finds no Gemini support claim
- **WHEN** maintainers run the documented Gemini audit across maintained source, tests, docs, demos, context, and system-skill roots
- **THEN** no non-exempt match represents a current Gemini provider workflow
- **AND THEN** every retained match belongs to an explicit historical or provider-neutral safety exclusion

