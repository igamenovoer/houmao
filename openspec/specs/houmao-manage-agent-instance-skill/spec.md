## Purpose
Define the packaged Houmao-owned `houmao-agent-instance` skill for managed-agent instance lifecycle guidance.
## Requirements
### Requirement: Houmao provides a packaged `houmao-agent-instance` system skill
The system SHALL package a Houmao-owned system skill named `houmao-agent-instance` under the maintained system-skill asset root.

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

That packaged skill SHALL remain the canonical Houmao-owned skill for general live managed-agent lifecycle guidance even when `houmao-specialist-mgr` also offers specialist-scoped `launch` and `stop` entry points with post-action handoff into this skill.

That packaged skill SHALL treat these surfaces as explicitly out of scope:

- `project easy specialist create|list|get|remove`
- `project easy instance list|get|stop`
- `agents prompt`, `agents interrupt`, `agents turn`, and `agents gateway ...`
- `agents mailbox ...`, `agents mail ...`, and `agents cleanup mailbox`
- `project mailbox ...` and `admin cleanup runtime ...`

#### Scenario: Installed skill points the agent at instance lifecycle commands
- **WHEN** an agent opens the installed `houmao-agent-instance` skill
- **THEN** the skill directs the agent to use the supported launch, join, list, stop, relaunch, and cleanup commands for managed-agent instances
- **AND THEN** it does not redirect the agent to ad hoc filesystem editing or unrelated runtime-control surfaces

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
- **AND THEN** it does not require `houmao-specialist-mgr` to become a general-purpose instance-management skill

### Requirement: `houmao-agent-instance` resolves the `houmao-mgr` launcher in the required precedence order
The packaged `houmao-agent-instance` skill SHALL instruct agents to resolve the `houmao-mgr` launcher for the current workspace using this default order unless the user explicitly requests a different launcher:

1. resolve `houmao-mgr` with `command -v houmao-mgr` and use the command found on `PATH`,
2. if that lookup fails, use the uv-managed fallback `uv tool run --from houmao houmao-mgr`,
3. if the PATH lookup and uv-managed fallback do not satisfy the turn, choose an appropriate development launcher such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, or project-local `uv run houmao-mgr`.

The skill SHALL treat the `command -v houmao-mgr` result as the ordinary first-choice launcher for the current turn.

The skill SHALL treat the uv-managed fallback as the ordinary non-PATH fallback because Houmao's documented installation path uses uv tools.

The skill SHALL only probe development-project hints such as `.venv`, Pixi files, `pyproject.toml`, or `uv.lock` after PATH resolution and uv fallback do not satisfy the turn, unless the user explicitly asks for a development launcher.

The skill SHALL honor an explicit user instruction to use a specific launcher family even when a higher-priority default launcher is available.

The resolved launcher SHALL be reused for any routed managed-agent instance action selected through the packaged skill.

#### Scenario: PATH launcher is preferred before development probing
- **WHEN** `command -v houmao-mgr` succeeds in the current workspace
- **THEN** the skill tells the agent to use that PATH-resolved `houmao-mgr` command for the turn
- **AND THEN** it does not probe `.venv`, Pixi, or project-local uv launchers first

#### Scenario: uv fallback is used when PATH lookup fails
- **WHEN** `command -v houmao-mgr` fails in the current workspace
- **THEN** the skill tells the agent to try `uv tool run --from houmao houmao-mgr`
- **AND THEN** it treats that uv-managed launcher as the ordinary next fallback because Houmao is officially installed through uv tools

#### Scenario: Development launchers are later defaults, not first probes
- **WHEN** `command -v houmao-mgr` fails
- **AND WHEN** the uv-managed fallback does not satisfy the turn
- **AND WHEN** the current workspace provides development launchers such as Pixi, repo-local `.venv`, or project-local uv
- **THEN** the skill tells the agent to choose an appropriate development launcher for that workspace
- **AND THEN** it does not treat those development launchers as the default first search path

#### Scenario: Explicit user launcher choice overrides the default order
- **WHEN** the user explicitly asks to use `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, project-local `uv run houmao-mgr`, or another specific launcher
- **THEN** the skill tells the agent to honor that requested launcher
- **AND THEN** it does not replace the user-requested launcher with the default PATH-first or uv-fallback choice

### Requirement: `houmao-agent-instance` selects the correct instance-lifecycle command and asks before guessing
The packaged `houmao-agent-instance` skill SHALL tell the agent to recover omitted lifecycle inputs from the current user prompt first and from recent chat context second when those values were stated explicitly.

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

### Requirement: `houmao-agent-instance` launch guidance preserves foreground-first gateway posture
The packaged `houmao-agent-instance` launch action guidance SHALL preserve foreground-first gateway posture whenever it teaches a launch lane that may start or inherit gateway attachment.

For specialist-backed launch through `project easy instance launch`, the guidance SHALL defer detailed launch-time gateway behavior to `houmao-specialist-mgr` while still stating that agents MUST NOT add background gateway flags unless the user explicitly requests detached background gateway execution.

For explicit launch-profile-backed managed launch, the guidance SHALL state that stored launch-profile gateway posture may already control gateway auto-attach, and agents SHALL NOT add one-shot background gateway overrides unless the user explicitly requests background gateway execution.

For direct role or preset launch through `agents launch`, the guidance SHALL avoid treating gateway attach as part of launch completion, while preserving the rule that any later gateway attach should go through `houmao-agent-gateway` foreground-first lifecycle guidance.

#### Scenario: Specialist-backed instance launch does not add background gateway flags
- **WHEN** an agent follows `houmao-agent-instance` launch guidance for the specialist-backed lane
- **AND WHEN** the user has not explicitly requested background gateway execution
- **THEN** the guidance does not add `--gateway-background` or another detached gateway override
- **AND THEN** it points detailed specialist-backed launch semantics to `houmao-specialist-mgr`

#### Scenario: Launch-profile lane does not override stored gateway posture silently
- **WHEN** an agent follows `houmao-agent-instance` guidance for `agents launch --launch-profile <profile>`
- **AND WHEN** the user has not explicitly requested a background gateway override
- **THEN** the guidance does not add a one-shot background gateway override
- **AND THEN** it treats the stored profile gateway posture as the source of launch-time gateway defaults

#### Scenario: Later gateway attach routes through foreground-first gateway guidance
- **WHEN** an agent completes a managed-agent launch where gateway attach is not part of launch completion
- **AND WHEN** the user then asks to attach or operate the live gateway
- **THEN** the guidance routes that follow-up through `houmao-agent-gateway`
- **AND THEN** the follow-up attach inherits the foreground-first and explicit-background rule from the gateway lifecycle guidance

