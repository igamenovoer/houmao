# houmao-agent-inspect-skill Specification

## Purpose
Help operators and agents inspect managed sessions through supported state surfaces and runtime evidence. Use gateway tracker data for TUI sessions and turn status or artifacts for headless sessions when available.
## Requirements
### Requirement: Houmao provides a packaged `houmao-agent-inspect` system skill
The system SHALL package a Houmao-owned system skill named `houmao-agent-inspect` under the maintained system-skill asset root.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

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
The packaged `houmao-agent-inspect` skill SHALL teach agents to resolve `houmao-mgr` for the current workspace. An explicit user choice SHALL take precedence over the default order of PATH lookup, the uv-managed fallback, and a development launcher.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

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

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The skill SHALL route generic managed-agent inspection in this order:

1. identify the target through scoped manager discovery or an explicit selector
2. read summary state through the scoped manager state command or the matching managed-agent `/state` route
3. consult managed transport detail and gateway observations when available and needed
4. inspect mailbox posture, logs, or runtime artifacts according to the requested domain
5. use a direct local tmux capture only when the actual pane is needed or the managed observations are insufficient

When the caller is already operating through the pair-managed HTTP seam, the skill SHALL allow the matching managed-agent `/houmao/agents/*` inspection routes. Generic discovery and supported record-backed inspection SHALL remain available without a live gateway.

#### Scenario: Missing target requires a user question
- **WHEN** the selected inspection action still lacks a required managed-agent selector after checking the current prompt and recent chat context
- **THEN** the skill tells the caller to ask the user for the missing selector before proceeding

#### Scenario: Generic inspection starts from summary state rather than raw tmux
- **WHEN** a caller asks what one managed agent is doing right now
- **THEN** the skill directs the caller to inspect scoped manager state or the matching managed-agent `/state` route first

#### Scenario: Pair-managed callers may use the detailed managed-agent route
- **WHEN** a caller is already operating through pair-managed HTTP control for one managed agent
- **THEN** the skill allows `GET /houmao/agents/{agent_ref}/state/detail` for transport-specific detail directly

#### Scenario: A detached gateway leaves supported observations available
- **WHEN** a caller asks for a peer's status and the peer has no attached gateway
- **THEN** the skill uses the available managed state and saved records and reports any observation limits

### Requirement: `houmao-agent-inspect` treats TUI and headless inspection differently
The inspect skill SHALL use managed state and detailed state to identify the agent's transport. For TUI tracking it SHALL prefer gateway TUI observations when available. For headless work it SHALL use managed turn state and logs. Direct local tmux capture SHALL require an authoritative recorded socket and exact target in an accessible execution-owner context.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

A direct local tmux capture SHALL specify the verified socket and pane. An explicitly requested attach SHALL use a verified socket-qualified handoff command or specify the socket and selected session. The fallback SHALL use the selected owner's exact server even when the caller is inside another server. The fallback SHALL report an unavailable exact target when that socket or target cannot be verified.

#### Scenario: TUI inspection prefers live gateway tracker state when available
- **WHEN** a caller asks to inspect the live tracked TUI state for one managed TUI agent and that agent currently has a healthy live gateway
- **THEN** the skill directs the caller to scoped `gateway tui state|history|watch` or the matching managed-agent gateway TUI routes for the requested evidence

#### Scenario: TUI raw pane peeking stays a local last-resort lane
- **WHEN** a caller explicitly asks to peek the actual local tmux pane for one TUI-backed managed agent
- **THEN** the skill uses managed records to verify the exact socket and pane in the execution owner's context
- **AND THEN** it shows direct capture with `tmux -S SOCKET capture-pane ... -t PANE` after managed observations
- **AND THEN** it reserves attach for an explicit request to attach

#### Scenario: Headless inspection uses managed detail and turn evidence
- **WHEN** a caller asks whether one managed headless agent is idle, active, or failed
- **THEN** the skill directs the caller to managed-agent detailed state and headless turn status or artifact surfaces

### Requirement: `houmao-agent-inspect` preserves mailbox and artifact boundaries
When the inspection task is about mailbox identity, unread state, or current live mailbox posture for one managed agent, the packaged `houmao-agent-inspect` skill SHALL direct the caller to:

- `houmao-mgr agents mail resolve-live`
- `houmao-mgr agents mail status`
- `houmao-mgr agents mail list`

When the inspection task is about late mailbox-binding posture for one local managed agent, the skill SHALL direct the caller to `houmao-mgr agents mailbox status`.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

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

### Requirement: Inspection separates agent selectors from transport overrides
The inspect skill SHALL use `agents single --agent-id ID` or `--agent-name NAME` for explicit selected-agent commands and verified `agents self` for current-session commands. When showing `--port` or `--pair-port`, it SHALL present the supported option as a transport override that still requires an explicit selected-agent identity.

#### Scenario: A named target uses an explicit passive server
- **WHEN** a caller supplies the name of a peer and an explicit transport port
- **THEN** the skill includes the target name in selected-agent scope
- **AND THEN** it uses the port only with the subordinate command that supports that option
