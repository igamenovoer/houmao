## MODIFIED Requirements

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
