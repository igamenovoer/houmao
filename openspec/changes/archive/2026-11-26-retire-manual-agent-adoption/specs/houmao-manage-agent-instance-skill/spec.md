# Spec Delta

## MODIFIED Requirements

### Requirement: Houmao provides a packaged `houmao-agent-instance` system skill
The system SHALL package a Houmao-owned system skill named `houmao-agent-instance` under the maintained system-skill asset root.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

That skill SHALL instruct agents to manage live managed-agent instances through these supported lifecycle commands:

- `houmao-mgr project agents launch`
- `houmao-mgr agents global list`
- `houmao-mgr agents single --agent-id <id> stop`
- `houmao-mgr agents single --agent-name <name> stop`
- `houmao-mgr agents self relaunch`
- `houmao-mgr agents single --agent-id <id> relaunch`
- `houmao-mgr agents single --agent-name <name> relaunch`
- `houmao-mgr agents single --agent-id <id> cleanup session|logs`
- `houmao-mgr agents single --agent-name <name> cleanup session|logs`

The top-level `SKILL.md` for that packaged skill SHALL serve as an index/router that selects one local action-specific document for:

- `launch`
- `list`
- `stop`
- `relaunch`
- `cleanup`

That packaged skill SHALL remain the canonical Houmao-owned skill for general live managed-agent lifecycle guidance even when `houmao-agent-definition` offers specialist-scoped `launch` and `stop` entry points with post-action handoff into this skill.

That packaged skill SHALL treat these surfaces as explicitly out of scope:

- `project specialist create|list|get|remove`
- ordinary prompt, interrupt, turn, gateway, mailbox, and mail work that is already owned by dedicated skills
- `project mailbox ...` and `admin cleanup runtime ...`

#### Scenario: Installed skill points the agent at scoped instance lifecycle commands
- **WHEN** an agent opens the installed `houmao-agent-instance` skill
- **THEN** the skill directs the agent to use the supported project launch, global list, and selected-agent stop, relaunch, and cleanup commands for managed-agent instances
- **AND THEN** it does not redirect the agent to ad hoc filesystem editing, manual session adoption, or removed root-level `agents list|stop|relaunch|cleanup` commands

#### Scenario: Installed skill routes to action-specific local guidance
- **WHEN** an agent reads the installed `houmao-agent-instance` skill
- **THEN** the top-level `SKILL.md` acts as an index/router for `launch`, `list`, `stop`, `relaunch`, and `cleanup`
- **AND THEN** the detailed per-action workflow lives in local action-specific documents rather than one flattened entry page

#### Scenario: Installed skill keeps mailbox and specialist CRUD out of scope
- **WHEN** an agent reads the installed `houmao-agent-instance` skill
- **THEN** the skill marks mailbox operations and specialist CRUD as outside the packaged skill scope
- **AND THEN** it does not present those actions as part of managed-agent instance lifecycle guidance

#### Scenario: Installed skill remains the follow-up lifecycle surface after specialist-scoped entry
- **WHEN** an agent or user reaches `houmao-agent-instance` after using specialist-scoped `launch` or `stop` guidance
- **THEN** the skill remains the canonical packaged Houmao-owned entry point for further live managed-agent lifecycle work
- **AND THEN** it does not require another specialist-authoring skill to become a general-purpose instance-management skill

### Requirement: Agent-instance skill excludes Gemini
The agent-instance skill SHALL NOT teach Gemini launch, relaunch, prompt, state, or cleanup workflows.

#### Scenario: Instance launch guidance has no Gemini branch
- **WHEN** an agent reads the packaged instance launch action
- **THEN** no supported provider example or caveat names Gemini

## ADDED Requirements

### Requirement: `houmao-agent-instance` selects a scoped lifecycle command for the requested operation
The packaged `houmao-agent-instance` skill SHALL tell the agent to recover omitted lifecycle inputs from the current user prompt first and from recent chat context second when those values were stated explicitly.

The skill SHALL NOT guess missing required inputs that are not explicit in current or recent conversation context.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The skill SHALL select commands by lifecycle source and target:

- use `houmao-mgr project agents launch --profile <profile>` or `houmao-mgr project agents launch --specialist <specialist>` for project-scoped managed-agent birth,
- use `houmao-mgr agents global list` for listing live local managed-agent instances,
- use `houmao-mgr agents single --agent-id <id> stop` or `houmao-mgr agents single --agent-name <name> stop` for stopping one selected live managed agent,
- use `houmao-mgr agents self relaunch` for current-session relaunch when the caller is inside the owning managed session,
- use `houmao-mgr agents single --agent-id <id> relaunch` or `houmao-mgr agents single --agent-name <name> relaunch` for selected-agent relaunch,
- use `houmao-mgr agents single --agent-id <id> cleanup session|logs` or `houmao-mgr agents single --agent-name <name> cleanup session|logs` for stopped-session artifact cleanup.

At minimum, the skill SHALL require the agent to obtain:

- for project launch: either a project profile or specialist source and any required instance name,
- for stop: a concrete managed-agent target
- for relaunch: either a concrete managed-agent target or enough current-session context to run the current-session relaunch form honestly
- for cleanup: a concrete cleanup kind plus one supported cleanup selector

The skill SHALL NOT route general lifecycle listing or selected-agent stop through `project agents list|get|stop` unless the user explicitly asks for the selected-project facade.

When relaunch is unavailable because the selected session lacks relaunch posture or the current-session authority cannot be resolved, the skill SHALL report relaunch as unavailable and SHALL NOT silently route that request through a fresh launch command without explicit user direction.

#### Scenario: Specialist-backed launch uses the project instance surface
- **WHEN** the user asks to launch an agent from an existing specialist
- **THEN** the skill directs the agent to use `houmao-mgr project agents launch --specialist <specialist>`
- **AND THEN** it does not redirect that request to a removed root-level `houmao-mgr agents launch` command

#### Scenario: Request to adopt a live manual session
- **WHEN** the user asks Houmao to take over an already-running provider session
- **THEN** the skill explains that local lifecycle management requires a managed launch
- **AND THEN** the skill directs the user to select a profile or specialist for a fresh project launch



#### Scenario: Live-instance list uses the global agents scope
- **WHEN** the user asks to list current managed-agent instances
- **THEN** the skill directs the agent to use `houmao-mgr agents global list`
- **AND THEN** it does not require a project-aware specialist instance listing path for that lifecycle view

#### Scenario: Explicit relaunch uses selected-agent scope
- **WHEN** the user asks to relaunch one managed agent and provides an explicit managed-agent name or id
- **THEN** the skill directs the agent to use `houmao-mgr agents single --agent-name <name> relaunch` or `houmao-mgr agents single --agent-id <id> relaunch`
- **AND THEN** it does not reinterpret that request as `project agents launch`

#### Scenario: Current-session relaunch uses self scope
- **WHEN** the user asks to relaunch from inside the owning tmux session and no explicit selector is required
- **THEN** the skill permits the current-session `houmao-mgr agents self relaunch` form
- **AND THEN** it does not require an unnecessary explicit target if current-session authority is already the intended relaunch contract

#### Scenario: Cleanup stays within selected-agent scope
- **WHEN** the user asks to clean instance artifacts after stop
- **THEN** the skill directs the agent to use `houmao-mgr agents single ... cleanup session` or `houmao-mgr agents single ... cleanup logs` as appropriate
- **AND THEN** it does not route that request to mailbox cleanup or broader admin cleanup surfaces

#### Scenario: Missing lifecycle target requires a user question
- **WHEN** the selected lifecycle action still lacks a required selector after checking the current prompt and recent chat context
- **THEN** the skill tells the agent to ask the user for the missing target before proceeding
- **AND THEN** it does not guess a role, specialist, live agent, or cleanup target

### Requirement: `houmao-agent-instance` documents supported lifecycle commands directly
The packaged `houmao-agent-instance` skill SHALL document supported lifecycle commands as direct fenced `bash` snippets or equivalent explicit command shapes.

The skill SHALL NOT reference `houmao-mgr internals command-templates`, command-template ids, template blockers, or command-template support when explaining lifecycle commands.

#### Scenario: Launch guidance shows the project command
- **WHEN** a user asks how to start a managed instance from a project profile
- **THEN** the skill shows `houmao-mgr project agents launch --profile <profile>` directly

## REMOVED Requirements

### Requirement: `houmao-agent-instance` selects the correct instance-lifecycle command and asks before guessing
**Reason**: Manual adoption guidance is retired.
**Migration**: Use the scoped lifecycle command for the managed target, or use project launch to start an agent.

### Requirement: `houmao-agent-instance` uses direct scoped command snippets for lifecycle command authoring
**Reason**: The manual adoption command example is retired.
**Migration**: Use the direct scoped launch and lifecycle command examples for managed agents.
