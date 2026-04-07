## Purpose
Define the packaged Houmao-owned `houmao-manage-agent-instance` skill for managed-agent instance lifecycle guidance.

## Requirements

### Requirement: Houmao provides a packaged `houmao-manage-agent-instance` system skill
The system SHALL package a Houmao-owned system skill named `houmao-manage-agent-instance` under the maintained system-skill asset root.

That skill SHALL instruct agents to manage live managed-agent instances through these supported lifecycle commands:

- `houmao-mgr agents launch`
- `houmao-mgr project easy instance launch`
- `houmao-mgr agents join`
- `houmao-mgr agents list`
- `houmao-mgr agents stop`
- `houmao-mgr agents relaunch`
- `houmao-mgr agents cleanup session`
- `houmao-mgr agents cleanup logs`

The top-level `SKILL.md` for that packaged skill SHALL serve as an index/router that selects one local action-specific document for:

- `launch`
- `join`
- `list`
- `stop`
- `relaunch`
- `cleanup`

That packaged skill SHALL remain the canonical Houmao-owned skill for general live managed-agent lifecycle guidance even when `houmao-manage-specialist` also offers specialist-scoped `launch` and `stop` entry points with post-action handoff into this skill.

That packaged skill SHALL treat these surfaces as explicitly out of scope:

- `project easy specialist create|list|get|remove`
- `project easy instance list|get|stop`
- `agents prompt`, `agents interrupt`, `agents turn`, and `agents gateway ...`
- `agents mailbox ...`, `agents mail ...`, and `agents cleanup mailbox`
- `project mailbox ...` and `admin cleanup runtime ...`

#### Scenario: Installed skill points the agent at instance lifecycle commands
- **WHEN** an agent opens the installed `houmao-manage-agent-instance` skill
- **THEN** the skill directs the agent to use the supported launch, join, list, stop, relaunch, and cleanup commands for managed-agent instances
- **AND THEN** it does not redirect the agent to ad hoc filesystem editing or unrelated runtime-control surfaces

#### Scenario: Installed skill routes to action-specific local guidance
- **WHEN** an agent reads the installed `houmao-manage-agent-instance` skill
- **THEN** the top-level `SKILL.md` acts as an index/router for `launch`, `join`, `list`, `stop`, `relaunch`, and `cleanup`
- **AND THEN** the detailed per-action workflow lives in local action-specific documents rather than one flattened entry page

#### Scenario: Installed skill keeps mailbox and specialist CRUD out of scope
- **WHEN** an agent reads the installed `houmao-manage-agent-instance` skill
- **THEN** the skill marks mailbox operations and specialist CRUD as outside the packaged skill scope
- **AND THEN** it does not present those actions as part of managed-agent instance lifecycle guidance

#### Scenario: Installed skill remains the follow-up lifecycle surface after specialist-scoped entry
- **WHEN** an agent or user reaches `houmao-manage-agent-instance` after using specialist-scoped `launch` or `stop` guidance
- **THEN** the skill remains the canonical packaged Houmao-owned entry point for further live managed-agent lifecycle work
- **AND THEN** it does not require `houmao-manage-specialist` to become a general-purpose instance-management skill

### Requirement: `houmao-manage-agent-instance` resolves the `houmao-mgr` launcher in the required precedence order
The packaged `houmao-manage-agent-instance` skill SHALL instruct agents to resolve the `houmao-mgr` launcher for the current workspace in this order:

1. repo-local `.venv` executable,
2. Pixi-managed project invocation,
3. project-local `uv run`,
4. globally installed `houmao-mgr` from uv tools.

The skill SHALL treat global uv-tools installation as the default end-user case when no development-project hints justify a repo-local launcher.

The skill SHALL tell the agent to look for development-project hints such as `.venv`, Pixi files, `pyproject.toml`, or `uv.lock` before choosing a repo-local launcher.

The resolved launcher SHALL be reused for any routed managed-agent instance action selected through the packaged skill.

#### Scenario: Repo-local `.venv` takes precedence over other launchers
- **WHEN** the current workspace provides `.venv/bin/houmao-mgr`
- **THEN** the skill tells the agent to use that repo-local executable first
- **AND THEN** it does not prefer Pixi, project-local `uv run`, or the global uv-tools install for that workspace

#### Scenario: Pixi-managed project takes precedence when no `.venv` launcher exists
- **WHEN** the current workspace has no repo-local `.venv` launcher
- **AND WHEN** the current workspace has Pixi development-project hints
- **THEN** the skill tells the agent to use `pixi run houmao-mgr`
- **AND THEN** it does not skip directly to project-local `uv run` or the global uv-tools install

#### Scenario: Project-local uv run is used when Pixi is absent
- **WHEN** the current workspace has no repo-local `.venv` launcher
- **AND WHEN** no Pixi-managed project hints are present
- **AND WHEN** the current workspace has project-local uv hints such as `uv.lock`
- **THEN** the skill tells the agent to use `uv run houmao-mgr`
- **AND THEN** it does not skip directly to the global uv-tools install

#### Scenario: Global uv-tools install remains the end-user default
- **WHEN** the current workspace does not provide repo-local `.venv`, Pixi, or project-local uv hints
- **THEN** the skill tells the agent to use the globally installed `houmao-mgr` command from uv tools
- **AND THEN** it treats that path as the ordinary end-user launcher

### Requirement: `houmao-manage-agent-instance` selects the correct instance-lifecycle command and asks before guessing
The packaged `houmao-manage-agent-instance` skill SHALL tell the agent to recover omitted lifecycle inputs from the current user prompt first and from recent chat context second when those values were stated explicitly.

The skill SHALL NOT guess missing required inputs that are not explicit in current or recent conversation context.

The skill SHALL select commands by lifecycle source and target:

- use `houmao-mgr agents launch` for launching one predefined role or preset
- use `houmao-mgr project easy instance launch` for launching one predefined specialist
- use `houmao-mgr agents join` for adopting one existing provider session into Houmao control
- use `houmao-mgr agents list` for listing live managed-agent instances
- use `houmao-mgr agents stop` for stopping one live managed agent
- use `houmao-mgr agents relaunch` for relaunching one tmux-backed managed-agent surface without rebuilding its home
- use `houmao-mgr agents cleanup session|logs` for cleaning stopped-session artifacts

At minimum, the skill SHALL require the agent to obtain:

- for direct launch: enough input to run `agents launch`, including the agent selector and provider
- for specialist-backed launch: the specialist name and instance name
- for join: the managed-agent name, and for headless join also the provider plus required launch args
- for stop: a concrete managed-agent target
- for relaunch: either a concrete managed-agent target or enough current-session context to run the current-session relaunch form honestly
- for cleanup: a concrete cleanup kind plus one supported cleanup selector

The skill SHALL NOT route specialist-backed runtime listing or stopping through `project easy instance list|get|stop`; once running, those instances SHALL be treated as managed agents on the canonical `agents` lifecycle surface.

When relaunch is unavailable because the selected session lacks relaunch posture or the current-session authority cannot be resolved, the skill SHALL report relaunch as unavailable and SHALL NOT silently route that request through a fresh launch command without explicit user direction.

#### Scenario: Specialist-backed launch uses the easy instance surface
- **WHEN** the user asks to launch an agent from an existing specialist
- **THEN** the skill directs the agent to use `houmao-mgr project easy instance launch`
- **AND THEN** it does not redirect that request to `houmao-mgr agents launch`

#### Scenario: Existing live-session adoption uses join
- **WHEN** the user asks Houmao to take over an already-running supported provider session
- **THEN** the skill directs the agent to use `houmao-mgr agents join`
- **AND THEN** it treats that join flow as creation of a managed-agent instance under Houmao control

#### Scenario: Live-instance list uses the canonical agents surface
- **WHEN** the user asks to list current managed-agent instances
- **THEN** the skill directs the agent to use `houmao-mgr agents list`
- **AND THEN** it does not require a project-aware specialist instance listing path for that lifecycle view

#### Scenario: Explicit relaunch uses the canonical agents relaunch surface
- **WHEN** the user asks to relaunch one managed agent and provides an explicit managed-agent name or id
- **THEN** the skill directs the agent to use `houmao-mgr agents relaunch`
- **AND THEN** it does not reinterpret that request as `agents launch` or `project easy instance launch`

#### Scenario: Current-session relaunch uses manifest-backed session context
- **WHEN** the user asks to relaunch from inside the owning tmux session and no explicit selector is required
- **THEN** the skill permits the current-session `houmao-mgr agents relaunch` form
- **AND THEN** it does not require an unnecessary explicit target if current-session authority is already the intended relaunch contract

#### Scenario: Relaunch-unavailable remains explicit instead of falling back to launch
- **WHEN** the selected relaunch path cannot be used because current-session authority is missing or the target session has no relaunch posture
- **THEN** the skill tells the agent to report that relaunch is unavailable
- **AND THEN** it does not silently replace the request with a fresh managed launch

#### Scenario: Cleanup stays within session and logs scope
- **WHEN** the user asks to clean instance artifacts after stop
- **THEN** the skill directs the agent to use `houmao-mgr agents cleanup session` or `houmao-mgr agents cleanup logs` as appropriate
- **AND THEN** it does not route that request to mailbox cleanup or broader admin cleanup surfaces

#### Scenario: Missing lifecycle target requires a user question
- **WHEN** the selected lifecycle action still lacks a required selector after checking the current prompt and recent chat context
- **THEN** the skill tells the agent to ask the user for the missing target before proceeding
- **AND THEN** it does not guess a role, specialist, live agent, or cleanup target
