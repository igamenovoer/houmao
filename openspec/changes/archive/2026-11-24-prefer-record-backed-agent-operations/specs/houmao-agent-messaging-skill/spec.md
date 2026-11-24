# Spec Delta

## MODIFIED Requirements

### Requirement: `houmao-agent-messaging` chooses the communication path that matches caller intent
The packaged `houmao-agent-messaging` skill SHALL tell the agent to recover omitted target selectors from the current user prompt first and from recent chat context second when those values were stated explicitly.

The skill SHALL NOT guess a missing required target or messaging intent that is not explicit in current or recent conversation context.

#### Scenario: Acceptance criteria

- **GIVEN** a case covered by this requirement
- **THEN** the applicable criteria below hold

The skill SHALL select commands by communication intent:

- use `houmao-mgr agents prompt` for a normal synchronous conversational turn
- use `houmao-mgr agents interrupt` for the transport-neutral interrupt path
- use `houmao-mgr agents gateway prompt|interrupt` when live-gateway queue semantics are required
- use `houmao-mgr agents gateway send-keys` when exact raw control input is required and the work must not be treated as a prompt turn
- use `houmao-mgr agents mail resolve-live` when the task needs mailbox discovery, current mailbox capability, or the exact live `gateway.base_url` before mailbox handoff
- use `houmao-mgr agents state` when the next action needs current runtime posture and `houmao-mgr agents gateway status` when it needs verified gateway status

For outbound agent mail, the skill SHALL use a known or resolved recipient address for the explicit channel and act through the sending agent's verified mailbox binding. It SHALL allow address discovery and delivery to a registered recipient independently of live runtime or gateway verification.

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

#### Scenario: Recipient contact is enough for ordinary mail

- **WHEN** a managed agent needs to send ordinary mail to a named peer
- **THEN** the skill uses the peer's known address or the peer's `mail resolve-live` result for the requested channel
- **AND THEN** the skill sends through `agents self mail send` without making the recipient's live state or gateway status a prerequisite

#### Scenario: Gateway is detached for a normal prompt

- **WHEN** a normal prompt is requested and the selected peer has no live gateway
- **THEN** the skill uses the scoped managed-agent prompt command through the recorded owner route if authorized and available
- **AND THEN** the skill reports unavailability when no authorized direct route can admit the prompt
