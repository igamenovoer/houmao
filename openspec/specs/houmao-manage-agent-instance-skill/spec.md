## Purpose
Define the packaged Houmao-owned `houmao-agent-instance` skill for managed-agent instance lifecycle guidance.
## Requirements
### Requirement: Houmao provides a packaged `houmao-agent-instance` system skill
The system SHALL package a Houmao-owned system skill named `houmao-agent-instance` under the maintained system-skill asset root.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

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
The packaged `houmao-agent-instance` skill SHALL teach agents to resolve `houmao-mgr` for the current workspace. An explicit user choice SHALL take precedence over the default order of PATH lookup, the uv-managed fallback, and a development launcher.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

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

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

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

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

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

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

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

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

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

### Requirement: Instance launch guidance respects the requested or stored run mode

The packaged instance guidance SHALL use `--mode` for an explicit birth override and otherwise preserve profile or tool defaults across direct role, preset, dossier, and specialist launches. It SHALL direct the operator to the reported terminal or browser handoff and keep operator policy separate from mode.

#### Scenario: Default specialist launch

- **WHEN** a caller starts a Claude or Codex specialist without a selected mode
- **THEN** the example omits an override and describes the TUI handoff supplied by the launch result

#### Scenario: Profile selects a nonterminal agent

- **WHEN** a stored profile requests an available Web or service mode
- **THEN** launch does not add a terminal override and the instructions use the actual handoff or manager/gateway control reference

#### Scenario: Headless is requested

- **WHEN** an operator explicitly asks for a one-shot provider CLI
- **THEN** the guidance shows `--mode headless` and does not infer a headless selection merely from unattended automation

### Requirement: Instance launch guidance resolves one-shot tmux selection
The instance launch workflow SHALL show the supported one-shot `project agents launch` tmux selector. It SHALL explain that a direct selector overrides the saved profile for that birth, while relaunch follows the recorded socket.

#### Scenario: One launch selects a different server from its profile
- **WHEN** a caller wants the shared Houmao server for one launch from a profile that selects a private server
- **THEN** the guidance shows `project agents launch --profile PROFILE --tmux-server houmao-default`
- **AND THEN** it explains that the execution owner's registry-backed shared server starts lazily at its recorded address and the saved profile retains its selector

#### Scenario: One launch selects an existing explicit socket
- **WHEN** the caller chooses `--tmux-server socket`
- **THEN** the guidance pairs it with `--tmux-socket-path` for an absolute path to a running server in the execution owner's context
- **AND THEN** it describes a missing or conflicting socket as a launch failure

#### Scenario: Launch leaves tmux selection to the existing precedence
- **WHEN** the caller leaves selection unspecified
- **THEN** the guidance preserves the saved profile selector or, when absent, uses the existing admitted executor or local scope, enclosing tmux, and native default fallback
- **AND THEN** it distinguishes `user-default`, `houmao-default`, `new`, and `socket` in the selector guidance

### Requirement: Instance skill routes native resource operations
The instance skill SHALL expose a `native-resources` command page for scoped `home`, `refresh --check`, and `refresh`. It SHALL use verified self or an explicitly selected agent within the caller's supported authority, and route authorized logical mount edits to `agent-files`.

#### Scenario: A managed agent asks about native resource freshness
- **WHEN** the verified managed caller needs to read its active native home or observe freshness
- **THEN** the guidance uses `agents self home` or `agents self refresh --check`
- **AND THEN** it explains that check reports common skill and MCP observations without requesting reload
- **AND THEN** it directs native-special-plugin inspection to the body's own facilities

#### Scenario: Native refresh returns a nonterminal or limited result
- **WHEN** scoped refresh reports automatic discovery, partial effects, busy state, or a restart requirement
- **THEN** the skill reports the observed state, native boundary, and result
- **AND THEN** it keeps managed launch-material regeneration and process restart in the separately selected relaunch workflow

#### Scenario: A peer requests a change on a managed mount
- **WHEN** the request concerns editing files on a gateway-owned logical mount
- **THEN** the skill delegates to `agent-files` and carries the selected agent forward
- **AND THEN** it treats the returned native home as diagnostic context
### Requirement: Agent instance manager covers external agents, executor bindings, launch flags, and relaunch behavior
`houmao-manage-agent-instance-skill` (`houmao-agent-instance`) SHALL cover `agents external {register|list|get|verify|remove}`, `--executor` and `admin executors reconcile|forget` boundaries, `open-browser` cross-link, `--headless-display-*`, `--tool-params`, `--reuse-home`, `--force`, `--agent-id-mode`, `--gateway-admin-seed`, and `relaunch` preservation of `--tmux-server` and mode plus DSH ACP `gateway detach`/`attach`.

#### Scenario: Operator launches, relaunches, or registers an external agent
- **WHEN** an admin launches with `--executor` / `--headless-display-*` / `--reuse-home` / `--force`, relaunches a DSH ACP session, or registers a remote peer via `agents external`
- **THEN** `commands/launch.md`, `commands/relaunch.md`, and `SKILL-MAIN.md` document exact flags, DSH ACP gateway re-attach requirements, and `agents external` local-only import semantics

### Requirement: Agent instance manager fixes duplicate guardrail and streamlines SKILL-MAIN.md and launch.md
`houmao-agent-instance` SHALL remove the duplicate `--purge-registry` guardrail in `commands/cleanup.md` (lines 38 and 40), replace repeated option lists in `commands/launch.md` with a clean options table (including `--tmux-server` on specialist-backed launches), and strip launcher, Missing-Input, `houmao-cli`, and Scope/Routing boilerplate in `SKILL-MAIN.md` (~95 lines).

#### Scenario: Cleanup guardrails and launch tables contain no duplication
- **WHEN** a reviewer inspects `houmao-agent-instance`
- **THEN** `commands/cleanup.md` contains no duplicate guardrail line, `commands/launch.md` presents launch options in a concise table, and `SKILL-MAIN.md` removes cross-skill boilerplate

### Requirement: Agent instance manager preserves actor scopes, state subsurfaces, and tmux server isolation
`houmao-agent-instance` SHALL preserve `## Actor Frame Gate`, admin vs `agents self` lifecycle scopes, `native-resources` (`home`, `refresh` never installing or editing gateway mounts), `runtime-variables` (CAS `--expected-revision`, no secrets), `mindsets` (fail-closed `snapshot`), `private-workspace` separation from `utils-workspace-mgr`, and `--tmux-server` isolation.

#### Scenario: Native refresh, runtime variables, and private workspace keep strict boundaries
- **WHEN** an agent or admin uses `native-resources`, `runtime-variables`, `mindsets`, or `private-workspace`
- **THEN** `refresh` does not mutate gateway mounts, `runtime-variables` stores no secrets, `mindsets` fails closed on snapshot failure, and `private-workspace` cleanup requires doctor, zero drift, and `--confirm`
