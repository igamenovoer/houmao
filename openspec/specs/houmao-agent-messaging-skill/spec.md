# houmao-agent-messaging-skill Specification

## Purpose
Define the packaged Houmao-owned system skill that routes communication and control for already-running managed agents.
## Requirements
### Requirement: Houmao provides a packaged `houmao-agent-messaging` system skill
The system SHALL package a Houmao-owned system skill named `houmao-agent-messaging` under the maintained system-skill asset root.

That skill SHALL instruct agents to communicate with already-existing Houmao-managed agents through these supported surfaces:

- `houmao-mgr agents state`
- `houmao-mgr agents gateway status`
- `houmao-mgr agents mail resolve-live`
- `houmao-mgr agents prompt`
- `houmao-mgr agents interrupt`
- `houmao-mgr agents gateway prompt`
- `houmao-mgr agents gateway interrupt`
- `houmao-mgr agents gateway send-keys`
- `houmao-mgr agents gateway tui state|history|note-prompt`
- managed-agent HTTP routes under `/houmao/agents/*`

The top-level `SKILL.md` for that packaged skill SHALL serve as an index/router that selects one local action-specific document for:

- `discover`
- `prompt`
- `interrupt`
- `gateway-queue`
- `send-keys`
- `mail-handoff`
- `reset-context`

That packaged skill SHALL remain the canonical Houmao-owned skill for communication with already-running managed agents whether the caller is another agent using an installed Houmao skill home or an external operator standing outside the managed session.

That packaged skill SHALL treat these surfaces as explicitly out of scope:

- `agents launch|join|stop|relaunch|cleanup`
- `project easy specialist create|list|get|remove`
- `project easy instance launch|list|get|stop`
- ordinary mailbox `status|check|read|send|reply|mark-read` operations
- mailbox transport-specific filesystem or Stalwart internals
- gateway attach and detach lifecycle work

#### Scenario: Installed skill points the agent at supported communication surfaces
- **WHEN** an agent opens the installed `houmao-agent-messaging` skill
- **THEN** the skill directs the agent to the supported prompt, interrupt, gateway, mailbox-discovery, and managed-agent HTTP surfaces
- **AND THEN** it does not redirect the agent to unrelated lifecycle or filesystem editing work

#### Scenario: Installed skill routes to action-specific local guidance
- **WHEN** an agent reads the installed `houmao-agent-messaging` skill
- **THEN** the top-level `SKILL.md` acts as an index/router for discovery, prompt, interrupt, gateway queue control, raw input, mailbox handoff, and reset-context guidance
- **AND THEN** the detailed workflow lives in local action-specific documents rather than in one flattened entry page

#### Scenario: Installed skill keeps lifecycle and mailbox-operation internals out of scope
- **WHEN** an agent reads the installed `houmao-agent-messaging` skill
- **THEN** the skill marks managed-agent lifecycle actions, ordinary mailbox operations, and mailbox transport internals as outside the packaged skill scope
- **AND THEN** it does not present launch, cleanup, or transport-local mailbox repair as part of messaging guidance

### Requirement: `houmao-agent-messaging` resolves the `houmao-mgr` launcher in the required precedence order
The packaged `houmao-agent-messaging` skill SHALL instruct agents to resolve the `houmao-mgr` launcher for the current workspace using this default order unless the user explicitly requests a different launcher:

1. resolve `houmao-mgr` with `command -v houmao-mgr` and use the command found on `PATH`,
2. if that lookup fails, use the uv-managed fallback `uv tool run --from houmao houmao-mgr`,
3. if the PATH lookup and uv-managed fallback do not satisfy the turn, choose an appropriate development launcher such as `pixi run houmao-mgr`, repo-local `.venv/bin/houmao-mgr`, or project-local `uv run houmao-mgr`.

The skill SHALL treat the `command -v houmao-mgr` result as the ordinary first-choice launcher for the current turn.

The skill SHALL treat the uv-managed fallback as the ordinary non-PATH fallback because Houmao's documented installation path uses uv tools.

The skill SHALL only probe development-project hints such as `.venv`, Pixi files, `pyproject.toml`, or `uv.lock` after PATH resolution and uv fallback do not satisfy the turn, unless the user explicitly asks for a development launcher.

The skill SHALL honor an explicit user instruction to use a specific launcher family even when a higher-priority default launcher is available.

The resolved launcher SHALL be reused for any routed messaging action selected through the packaged skill.

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

### Requirement: `houmao-agent-messaging` chooses the communication path that matches caller intent
The packaged `houmao-agent-messaging` skill SHALL tell the agent to recover omitted target selectors from the current user prompt first and from recent chat context second when those values were stated explicitly.

The skill SHALL NOT guess a missing required target or messaging intent that is not explicit in current or recent conversation context.

The skill SHALL select commands by communication intent:

- use `houmao-mgr agents prompt` for a normal synchronous conversational turn
- use `houmao-mgr agents interrupt` for the transport-neutral interrupt path
- use `houmao-mgr agents gateway prompt|interrupt` when live-gateway queue semantics are required
- use `houmao-mgr agents gateway send-keys` when exact raw control input is required and the work must not be treated as a prompt turn
- use `houmao-mgr agents mail resolve-live` when the task needs mailbox discovery, current mailbox capability, or the exact live `gateway.base_url` before mailbox handoff
- use `houmao-mgr agents state`, `houmao-mgr agents gateway status`, and `houmao-mgr agents mail resolve-live` as discovery surfaces before deeper gateway or mailbox routing

The skill SHALL prefer `houmao-mgr agents ...` and managed-agent `/houmao/agents/*` routes over direct gateway listener URLs when those higher-level surfaces already satisfy the current task.

#### Scenario: Ordinary conversation uses the default prompt path
- **WHEN** the user asks to send one normal message to a managed agent and wait for the turn outcome
- **THEN** the skill directs the agent to use `houmao-mgr agents prompt`
- **AND THEN** it does not redirect that ordinary request to queued gateway control or raw `send-keys`

#### Scenario: Raw terminal shaping uses send-keys instead of prompt submission
- **WHEN** the user needs slash-command menus, arrow navigation, `Escape`, or partial typing in a live TUI session
- **THEN** the skill directs the agent to use `houmao-mgr agents gateway send-keys`
- **AND THEN** it does not claim that raw terminal shaping is an ordinary prompt-turn workflow

#### Scenario: Queued control uses the gateway request surface
- **WHEN** the user explicitly wants live-gateway queue semantics instead of synchronous prompt completion
- **THEN** the skill directs the agent to use `houmao-mgr agents gateway prompt` or `houmao-mgr agents gateway interrupt`
- **AND THEN** it does not silently replace that request with the transport-neutral `agents prompt` or `agents interrupt` path

#### Scenario: Mailbox work uses discovery before handoff
- **WHEN** the user asks for mailbox-related work against a managed agent
- **THEN** the skill directs the agent to use `houmao-mgr agents mail resolve-live` or the equivalent managed-agent discovery route first when current mailbox posture or `gateway.base_url` is needed
- **AND THEN** it does not present `houmao-agent-messaging` as the owner of ordinary mailbox operations after that discovery

#### Scenario: Missing target requires a user question
- **WHEN** the selected messaging action still lacks a required target after checking the current prompt and recent chat context
- **THEN** the skill tells the agent to ask the user for the missing selector before proceeding
- **AND THEN** it does not guess the target managed agent

### Requirement: `houmao-agent-messaging` handles reset-context and lower-level gateway control honestly
The packaged `houmao-agent-messaging` skill SHALL describe clear-context and chat-session control using the currently implemented gateway control surfaces rather than inventing unsupported `houmao-mgr` flags.

For TUI-backed managed agents, the skill SHALL describe reset-then-send behavior through `POST /houmao/agents/{agent_ref}/gateway/control/prompt` or direct `POST /v1/control/prompt` with `chat_session.mode = "new"` when immediate clear-and-send control is required.

For headless managed agents, the skill SHALL describe both:

- direct prompt control with `chat_session.mode = "new"`, and
- one-shot next-prompt override through `POST /houmao/agents/{agent_ref}/gateway/control/headless/next-prompt-session` or direct `POST /v1/control/headless/next-prompt-session`

The skill SHALL state that direct gateway HTTP requires the exact live gateway base URL already present in current context or another supported discovery result, and SHALL NOT guess gateway host or port.

The skill SHALL state when the requested reset or chat-session behavior cannot stay entirely on the current `houmao-mgr` surface because the CLI does not yet expose a first-class flag for that behavior.

#### Scenario: TUI reset-context points to prompt-control with `mode = new`
- **WHEN** the user asks to clear context and immediately send a new prompt to a TUI-backed managed agent
- **THEN** the skill directs the agent to the managed-agent or direct gateway prompt-control route with `chat_session.mode = "new"`
- **AND THEN** it does not fabricate a nonexistent `houmao-mgr` reset-context flag

#### Scenario: Headless one-shot override uses next-prompt-session
- **WHEN** the user asks to prepare the next headless prompt for a fresh chat session without sending the prompt immediately
- **THEN** the skill directs the agent to the managed-agent or direct gateway `next-prompt-session` route
- **AND THEN** it does not misdescribe that one-shot override as a queued gateway prompt request

#### Scenario: Direct gateway URL is not guessed
- **WHEN** the requested reset or lower-level gateway operation would require direct gateway HTTP
- **AND WHEN** the current context does not provide an exact live gateway base URL
- **THEN** the skill does not guess a gateway host or port
- **AND THEN** it instead directs the agent to a supported higher-level managed-agent surface or reports that the required lower-level gateway endpoint is unavailable

### Requirement: `houmao-agent-messaging` delegates mailbox behavior to the current Houmao mailbox skills
When mailbox-related messaging requires notifier-round workflow, ordinary mailbox actions, or transport-specific guidance, the packaged `houmao-agent-messaging` skill SHALL direct the agent to the current Houmao mailbox skills instead of duplicating that detail locally.

At minimum, that delegation SHALL cover:

- `houmao-process-emails-via-gateway`
- `houmao-agent-email-comms`

The packaged `houmao-agent-messaging` skill SHALL keep its own mailbox coverage at the communication-routing and mailbox-handoff level and SHALL NOT restate filesystem layout, Stalwart credential handling, managed-agent mailbox operation routes, or the lower-level `/v1/mail/*` contract in full.

#### Scenario: Gateway mailbox round work delegates to the processing skill
- **WHEN** the messaging task becomes a notifier-driven mailbox-processing round with a live gateway mailbox facade
- **THEN** the skill directs the agent to `houmao-process-emails-via-gateway`
- **AND THEN** it does not duplicate that round workflow inside `houmao-agent-messaging`

#### Scenario: Ordinary mailbox work delegates to the unified ordinary-mailbox skill
- **WHEN** the messaging task needs ordinary mailbox work, live mailbox discovery follow-through, or transport-local mailbox guidance
- **THEN** the skill directs the agent to `houmao-agent-email-comms`
- **AND THEN** it does not restate that ordinary mailbox guidance as part of the generic managed-agent messaging skill

### Requirement: `houmao-agent-messaging` describes TUI interrupt as best-effort `Escape`
The packaged `houmao-agent-messaging` skill SHALL describe `houmao-mgr agents interrupt` as the default transport-neutral interrupt path for already-running managed agents.

For TUI-backed managed agents, the skill SHALL explain that ordinary interrupt means one best-effort `Escape` delivery and that the caller does not need to switch to raw `send-keys` merely to get that TUI interrupt behavior.

For TUI-backed managed agents, the skill SHALL explain that interrupt MAY still be useful when currently reported TUI state looks idle because tracked TUI state can lag the live visible surface.

For headless managed agents, the skill SHALL explain that ordinary interrupt targets active execution work and MAY return no-op semantics when no headless work is active.

The skill SHALL continue treating `houmao-mgr agents gateway send-keys` as the exact raw control-input path for slash menus, cursor movement, partial typing, or other precise TUI shaping.

#### Scenario: Skill describes ordinary TUI interrupt without redirecting to raw send-keys
- **WHEN** the user asks to interrupt a managed TUI agent
- **THEN** the skill directs the agent to use `houmao-mgr agents interrupt`
- **AND THEN** it explains that the TUI interrupt path delivers best-effort `Escape` rather than redirecting the caller to `houmao-mgr agents gateway send-keys`

#### Scenario: Skill explains delayed TUI tracking honestly
- **WHEN** the user asks why TUI interrupt may still be attempted while reported state looks idle
- **THEN** the skill explains that tracked TUI state can lag the live visible pane
- **AND THEN** it does not describe the idle tracked posture as proof that a TUI interrupt request would be meaningless

#### Scenario: Skill keeps headless interrupt semantics distinct
- **WHEN** the user asks to interrupt a managed headless agent
- **THEN** the skill explains that ordinary interrupt targets active execution work
- **AND THEN** it does not describe headless interrupt as unconditional `Escape` delivery

