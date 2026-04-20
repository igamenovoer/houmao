# houmao-agent-inspect-skill Specification

## Purpose
TBD - created by archiving change add-houmao-agent-inspect-skill. Update Purpose after archive.
## Requirements
### Requirement: Houmao provides a packaged `houmao-agent-inspect` system skill
The system SHALL package a Houmao-owned system skill named `houmao-agent-inspect` under the maintained system-skill asset root.

That skill SHALL instruct agents and operators to inspect Houmao-managed agents through these supported read-oriented surfaces:

- `houmao-mgr agents list`
- `houmao-mgr agents state`
- `houmao-mgr agents gateway status`
- `houmao-mgr agents gateway tui state|history|watch`
- `houmao-mgr agents mail resolve-live`
- `houmao-mgr agents mail status|check`
- `houmao-mgr agents mailbox status`
- `houmao-mgr agents turn status|events|stdout|stderr`
- managed-agent HTTP routes under `/houmao/agents/*`, including `/state`, `/state/detail`, `/history`, `/gateway`, `/gateway/tui/*`, and headless `/turns/*`
- runtime-owned managed-session artifacts such as `manifest.json`, `gateway/state.json`, `gateway/logs/gateway.log`, and headless turn-artifact files under the session root
- direct local tmux attach or pane capture only when the caller explicitly needs the live local pane or higher-level inspection surfaces are insufficient

The top-level `SKILL.md` for that packaged skill SHALL serve as an index/router that selects one local action-specific document for:

- `discover`
- `screen`
- `mailbox`
- `logs`
- `artifacts`

That packaged skill SHALL remain the canonical Houmao-owned skill for generic read-only managed-agent inspection.

That packaged skill SHALL treat these surfaces as explicitly out of scope:

- `agents prompt|interrupt`
- `agents gateway attach|detach|prompt|interrupt|send-keys`
- mailbox send, reply, post, mark, move, or archive work
- mailbox registration, repair, unregister, cleanup, or root administration
- agent stop, relaunch, cleanup, or other lifecycle mutation
- automatic invocation of the terminal recorder when the user did not explicitly ask for replay-grade capture

#### Scenario: Installed skill points the caller at supported inspection surfaces
- **WHEN** an agent or operator opens the installed `houmao-agent-inspect` skill
- **THEN** the skill directs the caller to supported managed-agent, gateway, mailbox, headless-turn, artifact, and tmux inspection surfaces
- **AND THEN** it does not present prompt submission, gateway mutation, mailbox mutation, or lifecycle control as part of generic inspection guidance

#### Scenario: Installed skill routes to action-specific local guidance
- **WHEN** a caller reads the installed `houmao-agent-inspect` skill
- **THEN** the top-level `SKILL.md` acts as an index/router for discovery, screen, mailbox, logs, and artifacts guidance
- **AND THEN** the detailed workflow lives in local action-specific documents rather than in one flattened entry page

#### Scenario: Installed skill keeps mutation out of scope
- **WHEN** a caller asks to inspect a managed agent and the next desired step would mutate that agent
- **THEN** the skill marks prompt, interrupt, gateway control, mailbox mutation, and lifecycle mutation as outside its packaged scope
- **AND THEN** it routes the caller to the owned operational skill instead of performing that mutation inside the inspection skill

### Requirement: `houmao-agent-inspect` resolves the `houmao-mgr` launcher in the required precedence order
The packaged `houmao-agent-inspect` skill SHALL instruct agents to resolve the `houmao-mgr` launcher for the current workspace using this default order unless the user explicitly requests a different launcher:

1. resolve `houmao-mgr` with `command -v houmao-mgr` and use the command found on `PATH`,
2. if that lookup fails, use the uv-managed fallback `uv tool run --from houmao houmao-mgr`,
3. if the PATH lookup and uv-managed fallback do not satisfy the turn, choose an appropriate development launcher such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, or project-local `uv run houmao-mgr`.

The skill SHALL treat the `command -v houmao-mgr` result as the ordinary first-choice launcher for the current turn.

The skill SHALL treat the uv-managed fallback as the ordinary non-PATH fallback because Houmao's documented installation path uses uv tools.

The skill SHALL only probe development-project hints such as `.venv`, Pixi files, `pyproject.toml`, or `uv.lock` after PATH resolution and uv fallback do not satisfy the turn, unless the user explicitly asks for a development launcher.

The skill SHALL honor an explicit user instruction to use a specific launcher family even when a higher-priority default launcher is available.

The resolved launcher SHALL be reused for any routed inspection action selected through the packaged skill.

#### Scenario: PATH launcher is preferred before development probing
- **WHEN** `command -v houmao-mgr` succeeds in the current workspace
- **THEN** the skill tells the agent to use that PATH-resolved `houmao-mgr` command for the turn
- **AND THEN** it does not probe `.venv`, Pixi, or project-local uv launchers first

#### Scenario: uv fallback is used when PATH lookup fails
- **WHEN** `command -v houmao-mgr` fails in the current workspace
- **THEN** the skill tells the agent to try `uv tool run --from houmao houmao-mgr`
- **AND THEN** it treats that uv-managed launcher as the ordinary next fallback because Houmao is officially installed through uv tools

#### Scenario: Explicit user launcher choice overrides the default order
- **WHEN** the user explicitly asks to use `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, project-local `uv run houmao-mgr`, or another specific launcher
- **THEN** the skill tells the agent to honor that requested launcher
- **AND THEN** it does not replace the user-requested launcher with the default PATH-first or uv-fallback choice

### Requirement: `houmao-agent-inspect` routes inspection through a supported evidence ladder
The packaged `houmao-agent-inspect` skill SHALL tell the caller to recover omitted target selectors from the current user prompt first and from recent chat context second when those values were stated explicitly.

The skill SHALL NOT guess a missing required target, transport kind, or inspection lane that is not explicit in current or recent conversation context.

The skill SHALL route generic managed-agent inspection in this order:

1. identify the target managed agent through `agents list` or an explicit selector
2. read summary state through `agents state` or the matching managed-agent `/state` route
3. use transport-specific detail through `/state/detail`, live gateway status, or live gateway TUI state when those surfaces are needed
4. inspect mailbox posture, logs, or runtime artifacts according to the requested inspection domain
5. use direct local tmux peeking only when the caller explicitly needs the visible pane or the supported surfaces are insufficient

When the caller is already operating through the pair-managed HTTP seam, the skill SHALL allow the matching managed-agent `/houmao/agents/*` inspection routes instead of forcing a CLI-only path.

#### Scenario: Missing target requires a user question
- **WHEN** the selected inspection action still lacks a required managed-agent selector after checking the current prompt and recent chat context
- **THEN** the skill tells the caller to ask the user for the missing selector before proceeding
- **AND THEN** it does not guess the target managed agent

#### Scenario: Generic inspection starts from summary state rather than raw tmux
- **WHEN** a caller asks what one managed agent is doing right now
- **THEN** the skill directs the caller to inspect `houmao-mgr agents state` or the matching managed-agent `/state` route first
- **AND THEN** it does not skip directly to tmux attach or filesystem spelunking as the default first step

#### Scenario: Pair-managed callers may use the detailed managed-agent route
- **WHEN** a caller is already operating through pair-managed HTTP control for one managed agent
- **THEN** the skill may direct that caller to `GET /houmao/agents/{agent_ref}/state/detail`
- **AND THEN** it does not require a second local-only tmux or filesystem path merely to reach transport-specific detail

### Requirement: `houmao-agent-inspect` treats TUI and headless inspection differently
For TUI-backed managed agents, the packaged `houmao-agent-inspect` skill SHALL treat these surfaces as the primary inspection ladder:

- `houmao-mgr agents state`
- `GET /houmao/agents/{agent_ref}/state/detail`
- `houmao-mgr agents gateway status`
- `houmao-mgr agents gateway tui state|history|watch` when a live gateway is attached

For TUI-backed managed agents, the skill SHALL position raw tmux attach or pane capture as a local last-resort lane rather than as the canonical first inspection surface.

For headless managed agents, the packaged skill SHALL treat these surfaces as the primary inspection ladder:

- `houmao-mgr agents state`
- `GET /houmao/agents/{agent_ref}/state/detail`
- `houmao-mgr agents turn status|events|stdout|stderr`

For headless managed agents, the skill SHALL NOT present auxiliary tmux topology as the primary inspection contract when managed headless detail and turn artifacts already expose the needed runtime posture.

#### Scenario: TUI inspection prefers live gateway tracker state when available
- **WHEN** a caller asks to inspect the live tracked TUI state for one managed TUI agent and that agent currently has a healthy live gateway
- **THEN** the skill directs the caller to `houmao-mgr agents gateway tui state|history|watch` or the matching managed-agent gateway TUI routes
- **AND THEN** it does not describe raw tmux capture as the canonical tracked-state contract for that request

#### Scenario: TUI raw pane peeking stays a local last-resort lane
- **WHEN** a caller explicitly asks to peek the actual local tmux pane for one TUI-backed managed agent
- **THEN** the skill allows direct local tmux attach or pane capture guidance
- **AND THEN** it still keeps that lane positioned after the supported managed-agent and gateway inspection surfaces

#### Scenario: Headless inspection uses managed detail and turn evidence
- **WHEN** a caller asks whether one managed headless agent is idle, active, or failed
- **THEN** the skill directs the caller to managed-agent detailed state and headless turn status or artifact surfaces
- **AND THEN** it does not require the caller to infer that posture primarily from tmux window topology

### Requirement: `houmao-agent-inspect` preserves mailbox and artifact boundaries
When the inspection task is about mailbox identity, unread state, or current live mailbox posture for one managed agent, the packaged `houmao-agent-inspect` skill SHALL direct the caller to:

- `houmao-mgr agents mail resolve-live`
- `houmao-mgr agents mail status`
- `houmao-mgr agents mail list`

When the inspection task is about late mailbox-binding posture for one local managed agent, the skill SHALL direct the caller to `houmao-mgr agents mailbox status`.

When the inspection task is about structural mailbox-root or projected-message state rather than actor-scoped mailbox follow-up, the skill SHALL direct the caller to `houmao-mailbox-mgr` instead of duplicating mailbox-admin guidance locally.

When the inspection task is about runtime artifacts, the packaged skill SHALL treat `manifest.json`, the session root, `gateway/state.json`, `gateway/logs/gateway.log`, and headless turn-artifact files as valid inspection targets.

The skill SHALL distinguish durable gateway state from disposable log artifacts and SHALL NOT describe gateway log files as the source of truth for queue or manifest state.

#### Scenario: Actor-scoped mailbox inspection uses the live mail surfaces
- **WHEN** a caller asks to inspect the current unread or mailbox identity state for one managed agent
- **THEN** the skill directs the caller to `agents mail resolve-live`, `agents mail status`, or `agents mail list` as appropriate
- **AND THEN** it does not misdescribe mailbox-root structural projection as the same thing as current unread follow-up state

#### Scenario: Structural mailbox inspection delegates to mailbox administration guidance
- **WHEN** a caller asks to inspect mailbox registrations or projected message files under one mailbox root
- **THEN** the skill directs the caller to `houmao-mailbox-mgr`
- **AND THEN** it does not duplicate mailbox-root administration detail inside the generic managed-agent inspection skill

#### Scenario: Gateway log inspection keeps durable state separate
- **WHEN** a caller asks to inspect the runtime artifacts behind one managed session with gateway capability
- **THEN** the skill allows inspection of `gateway/state.json`, `gateway/logs/gateway.log`, and other runtime-owned gateway files under the session root
- **AND THEN** it distinguishes durable gateway state files from disposable log-only artifacts
