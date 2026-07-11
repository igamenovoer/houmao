## Purpose
Define the packaged Houmao-owned `houmao-agent-instance` skill for managed-agent instance lifecycle guidance.
## Requirements
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

- use `houmao-mgr project agents launch --profile <profile>` or `houmao-mgr project agents launch --specialist <specialist>` for project-scoped managed-agent birth,
- use `houmao-mgr agents self join --agent-name <name>` for adopting the caller's current tmux session into Houmao control,
- use `houmao-mgr agents global list` for listing live local managed-agent instances,
- use `houmao-mgr agents single --agent-id <id> stop` or `houmao-mgr agents single --agent-name <name> stop` for stopping one selected live managed agent,
- use `houmao-mgr agents self relaunch` for current-session relaunch when the caller is inside the owning managed session,
- use `houmao-mgr agents single --agent-id <id> relaunch` or `houmao-mgr agents single --agent-name <name> relaunch` for selected-agent relaunch,
- use `houmao-mgr agents single --agent-id <id> cleanup session|logs` or `houmao-mgr agents single --agent-name <name> cleanup session|logs` for stopped-session artifact cleanup.

At minimum, the skill SHALL require the agent to obtain:

- for project launch: either a project profile or specialist source and any required instance name,
- for join: the managed-agent name, and for headless join also the provider plus required launch args
- for stop: a concrete managed-agent target
- for relaunch: either a concrete managed-agent target or enough current-session context to run the current-session relaunch form honestly
- for cleanup: a concrete cleanup kind plus one supported cleanup selector

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
- **AND THEN** it does not guess a role, specialist, live agent, or cleanup target

### Requirement: `houmao-agent-instance` launch guidance preserves foreground-first gateway posture
The packaged `houmao-agent-instance` launch action guidance SHALL preserve foreground-first gateway posture whenever it teaches a launch lane that may start or inherit gateway attachment.

For specialist-backed launch through `project agents launch`, the guidance SHALL defer detailed launch-time gateway behavior to `houmao-specialist-mgr` while still stating that agents MUST NOT add background gateway flags unless the user explicitly requests detached background gateway execution.

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

### Requirement: `houmao-agent-instance` cleanup guidance prefers durable post-stop locators
The packaged `houmao-agent-instance` cleanup guidance SHALL tell agents to use durable cleanup locators from stop output when cleaning artifacts after a stop action.

When recent stop output includes `manifest_path` or `session_root`, the guidance SHALL prefer `houmao-mgr agents cleanup session|logs --manifest-path <path>` or `--session-root <path>` over `--agent-id` or `--agent-name`.

When no durable path locator is available but the user provides a concrete `agent_id` or `agent_name`, the guidance MAY route cleanup through `--agent-id` or `--agent-name` and SHALL describe that selector cleanup can recover stopped sessions through bounded runtime-root fallback after live registry removal.

The guidance SHALL NOT instruct agents to create, search, or depend on stopped-session tombstones, stopped-agent indexes, or additional shared-registry state.

#### Scenario: Cleanup after stop uses manifest path from stop output
- **WHEN** an agent has recent stop output that includes `manifest_path = "/repo/.houmao/runtime/sessions/local_interactive/session-1/manifest.json"`
- **AND WHEN** the user asks to clean the stopped session envelope
- **THEN** the skill guidance directs the agent to use `houmao-mgr agents cleanup session --manifest-path /repo/.houmao/runtime/sessions/local_interactive/session-1/manifest.json`
- **AND THEN** it does not prefer a registry-only `--agent-name` selector for that post-stop cleanup

#### Scenario: Cleanup without path locator may use name or id fallback
- **WHEN** the user asks to clean stopped-session logs for managed agent `reviewer`
- **AND WHEN** recent context does not include a `manifest_path` or `session_root`
- **THEN** the skill guidance may direct the agent to use `houmao-mgr agents cleanup logs --agent-name reviewer`
- **AND THEN** the guidance acknowledges that stopped-session selector cleanup depends on runtime-root fallback if the live registry record has already been removed

#### Scenario: Cleanup guidance does not invent tombstones
- **WHEN** an agent follows `houmao-agent-instance` cleanup guidance for a stopped session
- **THEN** the guidance does not tell the agent to create or search a stopped-session tombstone or stopped-agent index
- **AND THEN** it stays within supported `houmao-mgr agents cleanup session|logs` selectors

### Requirement: `houmao-agent-instance` explains relaunch chat continuation
The packaged `houmao-agent-instance` skill SHALL explain that `houmao-mgr agents relaunch` can restart a relaunchable tmux-backed managed agent as either a fresh provider chat or a provider-native continuation when the implementation supports relaunch chat-session selection.

The skill SHALL route user requests to continue the previous provider chat during relaunch through `houmao-mgr agents relaunch` with the supported relaunch chat-session selector rather than through `agents launch` or ad hoc provider CLI commands.

The skill SHALL distinguish relaunch continuation from TUI prompt control: relaunch continuation happens at provider process startup, while TUI prompt control against an already-running surface remains a separate messaging/gateway concern.

The skill SHALL ask for a provider session id before selecting exact relaunch mode when the user has not supplied one.

#### Scenario: Skill routes latest-chat relaunch to agents relaunch
- **WHEN** the user asks to relaunch managed agent `reviewer` and continue the previous provider chat
- **THEN** the skill directs the agent to use `houmao-mgr agents relaunch --agent-name reviewer` with the latest-chat relaunch selector
- **AND THEN** it does not direct the agent to run `codex resume`, `claude --continue`, or `gemini --resume` outside Houmao control

#### Scenario: Skill asks before exact relaunch without id
- **WHEN** the user asks to relaunch into an exact provider chat
- **AND WHEN** no provider session id is present in the prompt or recent context
- **THEN** the skill tells the agent to ask for the missing provider session id
- **AND THEN** it does not guess an id from unrelated history

#### Scenario: Skill keeps fresh relaunch distinct from continuation
- **WHEN** the user asks for a normal relaunch and does not mention provider chat continuation
- **THEN** the skill keeps the default fresh relaunch behavior
- **AND THEN** it does not add continuation flags unprompted

### Requirement: `houmao-agent-instance` prefers TUI-supported launch posture when unspecified
The packaged `houmao-agent-instance` launch guidance SHALL instruct agents that omitted headless/TUI launch posture means "prefer TUI/local interactive when the selected tool or launch lane supports it."

For direct role or preset launch, launch-dossier-backed launch, and specialist-backed easy launch, the skill SHALL NOT add a one-shot `--headless` flag unless the user explicitly asks for headless execution or the selected tool/lane is known to require headless.

For profile-backed launch, the skill SHALL preserve explicit stored profile posture: an existing stored headless profile MAY launch headless, but the skill SHALL NOT add headless on top of an unspecified user request.

The skill SHALL keep prompt mode separate from launch posture and SHALL NOT treat unattended prompt mode, gateway attachment, mailbox defaults, output rendering, or automation-oriented wording as evidence that the user requested headless execution.

#### Scenario: Direct managed launch does not add headless by default
- **WHEN** a user asks `houmao-agent-instance launch` to launch from a role or preset for a TUI-capable tool
- **AND WHEN** the user does not request headless execution
- **THEN** the skill guidance directs the agent to omit `--headless`
- **AND THEN** the resulting command leaves launch posture TUI/local-interactive preferred when supported

#### Scenario: Raw-profile-backed launch does not add a headless override by default
- **WHEN** a user asks `houmao-agent-instance launch` to launch through an existing launch dossier
- **AND WHEN** the user does not request a headless one-shot override
- **THEN** the skill guidance directs the agent to omit `--headless`
- **AND THEN** it preserves whatever explicit posture is already stored on the selected profile

#### Scenario: Specialist-backed launch does not add headless by default
- **WHEN** a user asks `houmao-agent-instance launch` to launch from an existing Codex or Claude specialist
- **AND WHEN** the user does not request headless execution
- **THEN** the skill guidance directs the agent to omit `--headless`
- **AND THEN** it treats the launch as TUI/local-interactive preferred when supported

#### Scenario: Required-headless launch is not treated as the default
- **WHEN** a selected specialist or launch lane is known to require headless execution
- **THEN** the skill guidance may include the required headless flag or report the requirement
- **AND THEN** it explains that this is a tool or lane constraint rather than the default for unspecified launch posture

### Requirement: `houmao-agent-instance` uses direct scoped command snippets for lifecycle command authoring
The packaged `houmao-agent-instance` skill SHALL document supported lifecycle commands as direct fenced `bash` snippets or equivalent explicit command shapes.

The skill SHALL NOT reference `houmao-mgr internals command-templates`, command-template ids, template blockers, or command-template support when explaining lifecycle commands.

#### Scenario: Join guidance shows self join directly
- **WHEN** a user asks the skill how to adopt the current tmux session
- **THEN** the skill guidance shows `houmao-mgr agents self join --agent-name <managed-agent-name>`
- **AND THEN** it does not show `houmao-mgr agents join --name <managed-agent-name>`

### Requirement: Agent-instance skill excludes Gemini
The agent-instance skill SHALL NOT teach Gemini launch, join, relaunch, prompt, state, or cleanup workflows.

#### Scenario: Instance launch guidance has no Gemini branch
- **WHEN** an agent reads the packaged instance launch action
- **THEN** no supported provider example or caveat names Gemini
