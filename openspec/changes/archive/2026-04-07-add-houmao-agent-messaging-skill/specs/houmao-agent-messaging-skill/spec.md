## ADDED Requirements

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
- `houmao-mgr agents mail status|check|send|reply|mark-read`
- managed-agent HTTP routes under `/houmao/agents/*`

The top-level `SKILL.md` for that packaged skill SHALL serve as an index/router that selects one local action-specific document for:

- `discover`
- `prompt`
- `interrupt`
- `gateway-queue`
- `send-keys`
- `mail`
- `reset-context`

That packaged skill SHALL remain the canonical Houmao-owned skill for communication with already-running managed agents whether the caller is another agent using an installed Houmao skill home or an external operator standing outside the managed session.

That packaged skill SHALL treat these surfaces as explicitly out of scope:

- `agents launch|join|stop|relaunch|cleanup`
- `project easy specialist create|list|get|remove`
- `project easy instance launch|list|get|stop`
- mailbox transport-specific filesystem or Stalwart internals
- gateway attach and detach lifecycle work

#### Scenario: Installed skill points the agent at supported communication surfaces
- **WHEN** an agent opens the installed `houmao-agent-messaging` skill
- **THEN** the skill directs the agent to the supported prompt, interrupt, gateway, raw-input, mailbox, and managed-agent HTTP surfaces
- **AND THEN** it does not redirect the agent to unrelated lifecycle or filesystem editing work

#### Scenario: Installed skill routes to action-specific local guidance
- **WHEN** an agent reads the installed `houmao-agent-messaging` skill
- **THEN** the top-level `SKILL.md` acts as an index/router for discovery, prompt, interrupt, gateway queue control, raw input, mailbox, and reset-context guidance
- **AND THEN** the detailed workflow lives in local action-specific documents rather than in one flattened entry page

#### Scenario: Installed skill keeps lifecycle and mailbox-transport internals out of scope
- **WHEN** an agent reads the installed `houmao-agent-messaging` skill
- **THEN** the skill marks managed-agent lifecycle actions and mailbox transport internals as outside the packaged skill scope
- **AND THEN** it does not present launch, cleanup, or transport-local mailbox repair as part of messaging guidance

### Requirement: `houmao-agent-messaging` resolves the `houmao-mgr` launcher in the required precedence order
The packaged `houmao-agent-messaging` skill SHALL instruct agents to resolve the `houmao-mgr` launcher for the current workspace in this order:

1. repo-local `.venv` executable,
2. Pixi-managed project invocation,
3. project-local `uv run`,
4. globally installed `houmao-mgr` from uv tools.

The skill SHALL treat global uv-tools installation as the default end-user case when no development-project hints justify a repo-local launcher.

The skill SHALL tell the agent to look for development-project hints such as `.venv`, Pixi files, `pyproject.toml`, or `uv.lock` before choosing a repo-local launcher.

The resolved launcher SHALL be reused for any routed messaging action selected through the packaged skill.

#### Scenario: Repo-local `.venv` takes precedence over other launchers
- **WHEN** the current workspace provides `.venv/bin/houmao-mgr`
- **THEN** the skill tells the agent to use that repo-local executable first
- **AND THEN** it does not prefer Pixi, project-local `uv run`, or the global uv-tools install for that workspace

#### Scenario: Pixi-managed project takes precedence when no `.venv` launcher exists
- **WHEN** the current workspace has no repo-local `.venv` launcher
- **AND WHEN** the current workspace has Pixi development-project hints
- **THEN** the skill tells the agent to use `pixi run houmao-mgr`
- **AND THEN** it does not skip directly to project-local `uv run` or the global uv-tools install

#### Scenario: Global uv-tools install remains the end-user default
- **WHEN** the current workspace does not provide repo-local `.venv`, Pixi, or project-local uv hints
- **THEN** the skill tells the agent to use the globally installed `houmao-mgr` command from uv tools
- **AND THEN** it treats that path as the ordinary end-user launcher

### Requirement: `houmao-agent-messaging` chooses the communication path that matches caller intent
The packaged `houmao-agent-messaging` skill SHALL tell the agent to recover omitted target selectors from the current user prompt first and from recent chat context second when those values were stated explicitly.

The skill SHALL NOT guess a missing required target or messaging intent that is not explicit in current or recent conversation context.

The skill SHALL select commands by communication intent:

- use `houmao-mgr agents prompt` for a normal synchronous conversational turn
- use `houmao-mgr agents interrupt` for the transport-neutral interrupt path
- use `houmao-mgr agents gateway prompt|interrupt` when live-gateway queue semantics are required
- use `houmao-mgr agents gateway send-keys` when exact raw control input is required and the work must not be treated as a prompt turn
- use `houmao-mgr agents mail ...` when the target has mailbox capability and the work should be expressed as mailbox follow-up
- use `houmao-mgr agents state`, `houmao-mgr agents gateway status`, and `houmao-mgr agents mail resolve-live` as discovery surfaces before deeper gateway or mailbox follow-up

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

### Requirement: `houmao-agent-messaging` delegates transport-specific mailbox behavior to existing Houmao mailbox skills
When mailbox-related messaging requires transport-specific guidance or notifier-round workflow, the packaged `houmao-agent-messaging` skill SHALL direct the agent to the existing Houmao mailbox skills instead of duplicating that detail locally.

At minimum, that delegation SHALL cover:

- `houmao-process-emails-via-gateway`
- `houmao-email-via-agent-gateway`
- `houmao-email-via-filesystem`
- `houmao-email-via-stalwart`

The packaged `houmao-agent-messaging` skill SHALL keep its own mailbox coverage at the communication-routing level and SHALL NOT restate filesystem layout, Stalwart credential handling, or the lower-level `/v1/mail/*` contract in full.

#### Scenario: Gateway mailbox round work delegates to the processing skill
- **WHEN** the messaging task becomes a notifier-driven mailbox-processing round with a live gateway mailbox facade
- **THEN** the skill directs the agent to `houmao-process-emails-via-gateway`
- **AND THEN** it does not duplicate that round workflow inside `houmao-agent-messaging`

#### Scenario: Transport-specific mailbox questions delegate to the transport skill
- **WHEN** the messaging task needs filesystem-specific or Stalwart-specific mailbox behavior
- **THEN** the skill directs the agent to the appropriate transport-specific Houmao mailbox skill
- **AND THEN** it does not restate that transport-local guidance as part of the generic managed-agent messaging skill
