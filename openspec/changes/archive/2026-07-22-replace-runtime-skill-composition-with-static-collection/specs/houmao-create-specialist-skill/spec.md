## MODIFIED Requirements

### Requirement: `houmao-specialist-mgr` is no longer the canonical specialist-management skill
The system SHALL treat the `houmao-agent-definition` child of `houmao-shared-routines` as the canonical current owner for specialist and project-profile authoring.

`houmao-specialist-mgr` SHALL NOT remain a standalone `SKILL.md` root or an independent shared child. The admin entrypoint and direct shared skill SHALL retain `specialist-mgr` as a compatibility route alias that identifies agent-definition as canonical and delegates the supplied task without implementing separate commands.

#### Scenario: Old specialist route redirects to unified skill
- **WHEN** an admin or advanced direct caller uses the `specialist-mgr` route
- **THEN** the route identifies `houmao-agent-definition` as canonical
- **AND THEN** it delegates to the corresponding agent-definition operation
- **AND THEN** no compatibility skill directory is required

#### Scenario: Old specialist skill invocation redirects to unified skill
- **WHEN** a user or installed agent invokes `houmao-specialist-mgr` for specialist or project-profile authoring
- **THEN** the skill tells the agent to use the corresponding `houmao-agent-definition` easy subskill
- **AND THEN** it does not present itself as the independent canonical owner of specialist and project-profile workflows

#### Scenario: Old specialist wrapper invocation is encountered
- **WHEN** a user or migration check refers to `houmao-specialist-mgr`
- **THEN** Houmao identifies the admin entrypoint's agent-definition route as the replacement
- **AND THEN** it does not install or execute a compatibility wrapper


## ADDED Requirements

### Requirement: `houmao-specialist-mgr` compatibility wrapper routes renamed agent-definition subcommands
The `specialist-mgr` compatibility route alias SHALL map specialists, profiles, `create-agent-fast-forward`, `launch-agent`, and `stop-agent` to the canonical `houmao-agent-definition` child.

The alias SHALL use `create-agent-fast-forward` as the primary one-pass name and SHALL retain older ready-profile wording only as compatibility terminology. It SHALL be eligible only in admin or direct-admin posture.

#### Scenario: Compatibility alias names fast-forward path
- **WHEN** a caller uses `specialist-mgr` for one-pass profile preparation
- **THEN** the alias delegates to agent-definition's `create-agent-fast-forward` operation
- **AND THEN** it does not present ready-profile generation as an alias-owned workflow

#### Scenario: Compatibility wrapper names fast-forward path
- **WHEN** an agent opens `houmao-specialist-mgr`
- **THEN** the wrapper points one-pass profile preparation requests to `houmao-agent-definition` and `create-agent-fast-forward`
- **AND THEN** it does not present ready-profile generation as an independent wrapper-owned workflow


### Requirement: `houmao-specialist-mgr` delegates supported command authoring to config drafts and direct snippets
The `specialist-mgr` compatibility alias SHALL delegate supported specialist work to `houmao-agent-definition` for config-draft-backed preparation and direct executable command guidance.

The alias SHALL NOT duplicate command authoring, credential-kind references, launcher selection, mailbox behavior, or lifecycle behavior. Those preserved contracts SHALL remain inside the canonical child and its owned resources.

#### Scenario: Specialist create uses the compatibility alias
- **WHEN** a caller asks the alias to create a specialist
- **THEN** the alias passes the complete request to canonical agent-definition guidance
- **AND THEN** the canonical child applies its preserved config-draft or maintained direct-command contract

#### Scenario: Specialist launch uses the compatibility alias
- **WHEN** a caller asks the alias to launch a named specialist
- **THEN** the alias delegates to agent-definition's launch operation
- **AND THEN** missing inputs and posture conflicts are resolved by the canonical owner before execution

#### Scenario: Specialist create routes to draft-backed guidance
- **WHEN** a user asks `houmao-specialist-mgr` to create Codex specialist `reviewer` with credential `reviewer-creds`
- **THEN** the skill routes the work through `houmao-agent-definition` specialist guidance
- **AND THEN** that guidance uses config drafts or direct project commands without command-template rendering

#### Scenario: Specialist launch uses direct command guidance
- **WHEN** a user asks `houmao-specialist-mgr` to launch specialist `reviewer` as instance `reviewer-1`
- **THEN** the skill routes to direct `houmao-mgr project agents launch --specialist reviewer --name reviewer-1` guidance
- **AND THEN** missing inputs or conflicting posture requests are resolved before command execution

### Requirement: Canonical agent-definition preserves all specialist behavior
The shared agent-definition child SHALL preserve the pre-compaction specialist and project-profile operation inventory, launcher precedence, credential boundaries, provider-specific reference selection, mailbox launch behavior, foreground-first gateway posture, config-draft use, easy launch and stop handoffs, and broad-lifecycle boundary.

#### Scenario: Specialist operation moves under shared routines
- **WHEN** a user invokes the admin entrypoint's agent-definition route for specialist work
- **THEN** every original supported specialist operation remains available
- **AND THEN** only the packaging and actor-qualified route differ from the pre-compaction skill
