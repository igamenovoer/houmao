## ADDED Requirements

### Requirement: Command templates remain argv-oriented and do not own config drafts
`houmao-mgr internals command-templates` SHALL remain the internal surface for inspecting and rendering maintained `houmao-mgr` command argv.

Command templates SHALL NOT be treated as the primary agent-facing contract for project configuration YAML authoring when a matching `houmao-mgr internals config-drafts` draft id exists.

The command-template registry MAY continue to include entries for the underlying project commands so existing argv-rendering workflows keep working, but packaged skills SHALL prefer config drafts for draft-document authoring and command templates for executable command construction.

#### Scenario: Matching config draft supersedes command-template schema inspection for config authoring
- **WHEN** an agent needs a specialist-backed easy profile config document
- **AND WHEN** `internals config-drafts` provides `project.easy.profile`
- **THEN** maintained skill guidance uses the config draft surface for the YAML authoring shape
- **AND THEN** it does not require `internals command-templates show --id project.easy.profile.create` only to discover the full CLI option schema

#### Scenario: Command templates still render executable commands
- **WHEN** an agent needs to print or run a maintained `houmao-mgr` command that is not represented as a config document
- **THEN** the command-template renderer remains available for sparse intent to argv rendering
- **AND THEN** the config-draft surface does not need to mirror every command-oriented template id
