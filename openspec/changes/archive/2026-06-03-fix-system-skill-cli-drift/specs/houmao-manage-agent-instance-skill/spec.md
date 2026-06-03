## MODIFIED Requirements

### Requirement: Houmao provides a packaged `houmao-agent-instance` system skill
The system SHALL package a Houmao-owned system skill named `houmao-agent-instance` under the maintained system-skill asset root.

That skill SHALL instruct agents to manage live managed-agent instances through these supported lifecycle commands:

- `houmao-mgr project agents launch`
- `houmao-mgr agents self join`
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
- `join`
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
- **THEN** the skill directs the agent to use the supported project launch, self join, global list, and selected-agent stop, relaunch, and cleanup commands for managed-agent instances
- **AND THEN** it does not redirect the agent to ad hoc filesystem editing, removed root-level `agents join`, or removed root-level `agents list|stop|relaunch|cleanup` commands

#### Scenario: Installed skill routes to action-specific local guidance
- **WHEN** an agent reads the installed `houmao-agent-instance` skill
- **THEN** the top-level `SKILL.md` acts as an index/router for `launch`, `join`, `list`, `stop`, `relaunch`, and `cleanup`
- **AND THEN** the detailed per-action workflow lives in local action-specific documents rather than one flattened entry page

#### Scenario: Installed skill keeps mailbox and specialist CRUD out of scope
- **WHEN** an agent reads the installed `houmao-agent-instance` skill
- **THEN** the skill marks mailbox operations and specialist CRUD as outside the packaged skill scope
- **AND THEN** it does not present those actions as part of managed-agent instance lifecycle guidance

#### Scenario: Installed skill remains the follow-up lifecycle surface after specialist-scoped entry
- **WHEN** an agent or user reaches `houmao-agent-instance` after using specialist-scoped `launch` or `stop` guidance
- **THEN** the skill remains the canonical packaged Houmao-owned entry point for further live managed-agent lifecycle work
- **AND THEN** it does not require another specialist-authoring skill to become a general-purpose instance-management skill

### Requirement: `houmao-agent-instance` selects the correct instance-lifecycle command and asks before guessing
The packaged `houmao-agent-instance` skill SHALL tell the agent to recover omitted lifecycle inputs from the current user prompt first and from recent chat context second when those values were stated explicitly.

The skill SHALL NOT guess missing required inputs that are not explicit in current or recent conversation context.

The skill SHALL select commands by lifecycle source and target:

- use `houmao-mgr project agents launch --profile <profile>` or `houmao-mgr project agents launch --specialist <specialist>` for project-scoped managed-agent birth,
- use `houmao-mgr agents self join --agent-name <name>` for adopting the caller's current tmux session into Houmao control,
- use `houmao-mgr agents global list` for listing live local managed-agent instances,
- use `houmao-mgr agents single --agent-id <id> stop` or `houmao-mgr agents single --agent-name <name> stop` for stopping one selected live managed agent,
- use `houmao-mgr agents self relaunch` for current-session relaunch when the caller is inside the owning managed session,
- use `houmao-mgr agents single --agent-id <id> relaunch` or `houmao-mgr agents single --agent-name <name> relaunch` for selected-agent relaunch,
- use `houmao-mgr agents single --agent-id <id> cleanup session|logs` or `houmao-mgr agents single --agent-name <name> cleanup session|logs` for stopped-session artifact cleanup.

At minimum, the skill SHALL require the agent to obtain:

- for project launch: either a project profile or specialist source and any required instance name,
- for join: the managed-agent name, and for headless join also the provider plus required launch args,
- for stop: a concrete managed-agent target,
- for relaunch: either a concrete managed-agent target or enough current-session context to run the current-session relaunch form honestly,
- for cleanup: a concrete cleanup kind plus one supported cleanup selector.

The skill SHALL NOT route general lifecycle listing or selected-agent stop through `project agents list|get|stop` unless the user explicitly asks for the selected-project facade.

When relaunch is unavailable because the selected session lacks relaunch posture or the current-session authority cannot be resolved, the skill SHALL report relaunch as unavailable and SHALL NOT silently route that request through a fresh launch command without explicit user direction.

#### Scenario: Specialist-backed launch uses the project instance surface
- **WHEN** the user asks to launch an agent from an existing specialist
- **THEN** the skill directs the agent to use `houmao-mgr project agents launch --specialist <specialist>`
- **AND THEN** it does not redirect that request to a removed root-level `houmao-mgr agents launch` command

#### Scenario: Existing live-session adoption uses self join
- **WHEN** the user asks Houmao to take over an already-running supported provider session
- **THEN** the skill directs the agent to use `houmao-mgr agents self join --agent-name <name>`
- **AND THEN** it treats that join flow as current-session adoption rather than selected-agent lifecycle work

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
- **AND THEN** it does not guess a specialist, live agent, or cleanup target

## REMOVED Requirements

### Requirement: `houmao-agent-instance` uses CLI-owned templates for lifecycle command authoring
**Reason**: The command-template renderer has been retired; lifecycle executable commands are documented directly in the packaged skill.

**Migration**: Use fenced `bash` snippets for `project agents launch`, `agents self join`, `agents global list`, `agents self relaunch`, `agents single ... relaunch`, and `agents single ... cleanup ...`.

#### Scenario: Lifecycle command authoring no longer uses template rendering
- **WHEN** an agent reads `houmao-agent-instance` command guidance
- **THEN** it sees direct scoped `houmao-mgr` commands
- **AND THEN** it is not told to render a command-template id first

## ADDED Requirements

### Requirement: `houmao-agent-instance` uses direct scoped command snippets for lifecycle command authoring
The packaged `houmao-agent-instance` skill SHALL document supported lifecycle commands as direct fenced `bash` snippets or equivalent explicit command shapes.

The skill SHALL NOT reference `houmao-mgr internals command-templates`, command-template ids, template blockers, or command-template support when explaining lifecycle commands.

#### Scenario: Join guidance shows self join directly
- **WHEN** a user asks the skill how to adopt the current tmux session
- **THEN** the skill guidance shows `houmao-mgr agents self join --agent-name <managed-agent-name>`
- **AND THEN** it does not show `houmao-mgr agents join --name <managed-agent-name>`
