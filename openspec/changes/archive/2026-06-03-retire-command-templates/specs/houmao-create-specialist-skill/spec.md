## REMOVED Requirements

### Requirement: `houmao-specialist-mgr` delegates supported command authoring to CLI-owned templates
**Reason**: Specialist command templates are retired with the command-template renderer.
**Migration**: Delegate specialist/profile authoring to `houmao-agent-definition` config-draft and direct-command guidance, or document direct `houmao-mgr project specialist ...` and `houmao-mgr project agents launch ...` commands where the wrapper remains responsible.

#### Scenario: Specialist authoring does not use templates
- **WHEN** the compatibility skill documents specialist create, update, or launch
- **THEN** it uses config drafts or direct command snippets rather than command-template ids

### Requirement: `houmao-specialist-mgr` treats template blockers as user-facing recovery points
**Reason**: Template blockers are retired with the command-template renderer.
**Migration**: The skill itself SHALL detect missing required input and explicit conflicts before running direct commands.

#### Scenario: Blocker recovery becomes skill-owned
- **WHEN** a specialist request is missing required input or contains conflicting posture instructions
- **THEN** the skill asks the user for clarification before running any direct command

## ADDED Requirements

### Requirement: `houmao-specialist-mgr` delegates supported command authoring to config drafts and direct snippets
The packaged `houmao-specialist-mgr` compatibility skill SHALL route supported specialist work to `houmao-agent-definition` for config-draft-backed preparation and direct executable command guidance.

When the compatibility skill documents a command itself, it SHALL use fenced `bash` snippets for direct maintained `houmao-mgr` commands.

The skill SHALL NOT reference `houmao-mgr internals command-templates show`, `houmao-mgr internals command-templates render`, command-template ids, or template blockers.

#### Scenario: Specialist create routes to draft-backed guidance
- **WHEN** a user asks `houmao-specialist-mgr` to create Codex specialist `reviewer` with credential `reviewer-creds`
- **THEN** the skill routes the work through `houmao-agent-definition` specialist guidance
- **AND THEN** that guidance uses config drafts or direct project commands without command-template rendering

#### Scenario: Specialist launch uses direct command guidance
- **WHEN** a user asks `houmao-specialist-mgr` to launch specialist `reviewer` as instance `reviewer-1`
- **THEN** the skill routes to direct `houmao-mgr project agents launch --specialist reviewer --name reviewer-1` guidance
- **AND THEN** missing inputs or conflicting posture requests are resolved before command execution
